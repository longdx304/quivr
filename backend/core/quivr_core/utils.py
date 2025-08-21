import logging
from typing import Any, List, Tuple, no_type_check

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.ai import AIMessageChunk
from langchain_core.prompts import format_document

from quivr_core.models import (
    ParsedRAGResponse,
    QuivrKnowledge,
    RAGResponseMetadata,
    RawRAGResponse,
)
from quivr_core.prompts import custom_prompts

# TODO(@aminediro): define a types packages where we clearly define IO types
# This should be used for serialization/deseriallization later


logger = logging.getLogger("quivr_core")


def model_supports_function_calling(model_name: str):
    models_supporting_function_calls = [
        "gpt-4",
        "gpt-4-1106-preview",
        "gpt-4-0613",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo-0613",
        "gpt-4-0125-preview",
        "gpt-3.5-turbo",
        "gpt-4-turbo",
        "gpt-4o",
        "gpt-4o-mini",
        "claude-3-5-sonnet-20241022",
        "gpt-4.1-mini"
    ]
    return model_name in models_supporting_function_calls


def format_history_to_openai_mesages(
    tuple_history: List[Tuple[str, str]], system_message: str, question: str
) -> List[BaseMessage]:
    """Format the chat history into a list of Base Messages"""
    messages = []
    messages.append(SystemMessage(content=system_message))
    for human, ai in tuple_history:
        messages.append(HumanMessage(content=human))
        messages.append(AIMessage(content=ai))
    messages.append(HumanMessage(content=question))
    return messages


def cited_answer_filter(tool):
    return tool["name"] == "cited_answer"


def filter_sources_by_temporal_context(sources: list[Any], user_question: str) -> list[Any]:
    """
    Filter sources to prioritize documents that match the temporal context of user question.
    This prevents mixing sources from different months/years (e.g., doc_template.md vs doc_template-1.md).
    """
    if not sources or len(sources) <= 1:
        return sources
    
    # Extract temporal hints from user question
    temporal_hints = {
        "month_4": ["tháng 4", "4/2025", "04/2025", "april"],
        "month_1": ["tháng 1", "1/2025", "01/2025", "january"],
        "month_2": ["tháng 2", "2/2025", "02/2025", "february"],
        "month_3": ["tháng 3", "3/2025", "03/2025", "march"],
        "month_5": ["tháng 5", "5/2025", "05/2025", "may"],
    }
    
    user_question_lower = user_question.lower()
    detected_month = None
    
    for month, hints in temporal_hints.items():
        if any(hint in user_question_lower for hint in hints):
            detected_month = month
            break
    
    # If no temporal hint detected, return all sources
    if not detected_month:
        return sources
    
    # Group sources by document identifier and temporal context
    source_groups = {}
    for source in sources:
        doc_metadata = getattr(source, 'metadata', {})
        filename = doc_metadata.get('filename', '')
        document_month = doc_metadata.get('document_month')
        document_identifier = doc_metadata.get('document_identifier', filename)
        
        # Create grouping key based on temporal context
        if document_month:
            month_key = f"month_{document_month}"
            group_key = f"{month_key}_{document_identifier}"
        else:
            # Fallback to filename analysis
            if "template-1" in filename.lower():
                group_key = "month_1_" + filename
            elif "template" in filename.lower() and "-1" not in filename.lower():
                group_key = "month_4_" + filename
            else:
                group_key = "unknown_" + filename
        
        if group_key not in source_groups:
            source_groups[group_key] = []
        source_groups[group_key].append(source)
    
    # Prioritize sources matching detected temporal context
    if detected_month:
        matching_sources = []
        for group_key, group_sources in source_groups.items():
            if group_key.startswith(detected_month):
                matching_sources.extend(group_sources)
        
        # If we found matching sources, return only those
        if matching_sources:
            logger.info(f"Filtered sources to {len(matching_sources)} documents matching temporal context: {detected_month}")
            return matching_sources
    
    # If no specific match, return sources from the largest group (most relevant)
    largest_group = max(source_groups.values(), key=len) if source_groups else sources
    return largest_group


def get_chunk_metadata(
    msg: AIMessageChunk, sources: list[Any] | None = None, user_question: str = ""
) -> RAGResponseMetadata:
    # Filter sources by temporal context to prevent mixing documents from different periods
    filtered_sources = filter_sources_by_temporal_context(sources or [], user_question) if sources else []
    
    # Initiate the source
    metadata = {"sources": filtered_sources} if filtered_sources else {"sources": []}
    if msg.tool_calls:
        cited_answer = next(x for x in msg.tool_calls if cited_answer_filter(x))

        if "args" in cited_answer:
            gathered_args = cited_answer["args"]
            if "citations" in gathered_args:
                citations = gathered_args["citations"]
                metadata["citations"] = citations

            if "followup_questions" in gathered_args:
                followup_questions = gathered_args["followup_questions"]
                metadata["followup_questions"] = followup_questions

    return RAGResponseMetadata(**metadata, metadata_model=None)


def get_prev_message_str(msg: AIMessageChunk) -> str:
    if msg.tool_calls:
        cited_answer = next(x for x in msg.tool_calls if cited_answer_filter(x))
        if "args" in cited_answer and "answer" in cited_answer["args"]:
            return cited_answer["args"]["answer"]
    return ""


# TODO: CONVOLUTED LOGIC !
# TODO(@aminediro): redo this
@no_type_check
def parse_chunk_response(
    rolling_msg: AIMessageChunk,
    raw_chunk: dict[str, Any],
    supports_func_calling: bool,
) -> Tuple[AIMessageChunk, str]:
    # Init with sources
    answer_str = ""

    if "answer" in raw_chunk:
        answer = raw_chunk["answer"]
    else:
        answer = raw_chunk

    rolling_msg += answer
    if supports_func_calling and rolling_msg.tool_calls:
        cited_answer = next(x for x in rolling_msg.tool_calls if cited_answer_filter(x))
        if "args" in cited_answer and "answer" in cited_answer["args"]:
            gathered_args = cited_answer["args"]
            # Only send the difference between answer and response_tokens which was the previous answer
            answer_str = gathered_args["answer"]
            return rolling_msg, answer_str

    return rolling_msg, answer.content


@no_type_check
def parse_response(raw_response: RawRAGResponse, model_name: str) -> ParsedRAGResponse:
    answer = ""
    metadata = {}
    if (
        model_supports_function_calling(model_name)
        and hasattr(raw_response["answer"], "tool_calls")
        and raw_response["answer"].tool_calls
    ):
        if "citations" in raw_response["answer"].tool_calls[-1]["args"]:
            citations = raw_response["answer"].tool_calls[-1]["args"]["citations"]
            metadata["citations"] = citations
            followup_questions = raw_response["answer"].tool_calls[-1]["args"][
                "followup_questions"
            ]
            if followup_questions:
                metadata["followup_questions"] = followup_questions
            answer = raw_response["answer"].tool_calls[-1]["args"]["answer"]
        else:
            answer = raw_response["answer"].tool_calls[-1]["args"]["answer"]
    else:
        answer = raw_response["answer"].content
    parsed_response = ParsedRAGResponse(
        answer=answer,
        metadata=RAGResponseMetadata(**metadata, metadata_model=None),
    )
    return parsed_response


def combine_documents(
    docs,
    document_prompt=custom_prompts.DEFAULT_DOCUMENT_PROMPT,
    document_separator="\n\n",
):
    # for each docs, add an index in the metadata to be able to cite the sources
    for doc, index in zip(docs, range(len(docs)), strict=False):
        doc.metadata["index"] = index
    doc_strings = [format_document(doc, document_prompt) for doc in docs]
    return document_separator.join(doc_strings)


def format_file_list(
    list_files_array: list[QuivrKnowledge], max_files: int = 20
) -> str:
    list_files = [file.file_name or file.url for file in list_files_array]
    files: list[str] = list(filter(lambda n: n is not None, list_files))  # type: ignore
    files = files[:max_files]

    files_str = "\n".join(files) if list_files_array else "None"
    return files_str
