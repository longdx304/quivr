import logging
from typing import Any, List, Tuple, no_type_check

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.messages.ai import AIMessageChunk
from langchain_core.prompts import format_document

from quivr_core.models import (
    ChatLLMMetadata,
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


def get_chunk_metadata(
    msg: AIMessageChunk, sources: list[Any] | None = None
) -> RAGResponseMetadata:
    # Initiate the source
    metadata = {"sources": sources} if sources else {"sources": []}
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
    sources = raw_response["docs"] if "docs" in raw_response else []

    metadata = RAGResponseMetadata(
        sources=sources, metadata_model=ChatLLMMetadata(name=model_name)
    )

    if (
        model_supports_function_calling(model_name)
        and "tool_calls" in raw_response["answer"]
        and raw_response["answer"].tool_calls
    ):
        if "citations" in raw_response["answer"].tool_calls[-1]["args"]:
            citations = raw_response["answer"].tool_calls[-1]["args"]["citations"]
            metadata.citations = citations
            followup_questions = raw_response["answer"].tool_calls[-1]["args"][
                "followup_questions"
            ]
            if followup_questions:
                metadata.followup_questions = followup_questions
            answer = raw_response["answer"].tool_calls[-1]["args"]["answer"]
        else:
            answer = raw_response["answer"].tool_calls[-1]["args"]["answer"]
    else:
        answer = raw_response["answer"].content

    # Validate source attribution in the generated answer
    if answer and sources:
        attribution_validation = validate_source_attribution(answer, sources)
        
        # Add validation results to metadata
        metadata.attribution_validation = attribution_validation
        
        # Log warnings for poor attribution
        if attribution_validation["attribution_score"] < 0.5:
            logger.warning(
                f"Poor source attribution detected. Score: {attribution_validation['attribution_score']:.2f}. "
                f"Suggestions: {'; '.join(attribution_validation['suggestions'])}"
            )
    
    parsed_response = ParsedRAGResponse(answer=answer, metadata=metadata)
    return parsed_response


def combine_documents(
    docs,
    document_prompt=custom_prompts.DEFAULT_DOCUMENT_PROMPT,
    document_separator="\n\n",
):
    """
    Enhanced document combination with source organization and metadata enrichment.
    Groups documents by source and provides clear separation to prevent information mixing.
    """
    if not docs:
        return "No documents available."
    
    # Enhanced metadata for each document
    for doc, index in zip(docs, range(len(docs)), strict=False):
        doc.metadata["index"] = index
        
        # Extract meaningful identifiers from metadata
        file_name = doc.metadata.get("file_name", doc.metadata.get("source", f"Document_{index}"))
        page = doc.metadata.get("page", doc.metadata.get("page_number", "N/A"))
        content_type = doc.metadata.get("content_type", doc.metadata.get("type", "text"))
        
        # Enrich metadata for better source identification
        doc.metadata["file_name"] = file_name
        doc.metadata["page"] = page
        doc.metadata["content_type"] = content_type
    
    # Group documents by source file to prevent mixing
    grouped_docs = {}
    for doc in docs:
        source_key = doc.metadata.get("file_name", f"Unknown_Source_{doc.metadata['index']}")
        if source_key not in grouped_docs:
            grouped_docs[source_key] = []
        grouped_docs[source_key].append(doc)
    
    # Format documents with enhanced source separation
    if len(grouped_docs) > 1:
        # Multiple sources - use grouped format with clear separation
        formatted_groups = []
        global_index = 0
        
        for source_name, source_docs in grouped_docs.items():
            group_header = f"\n\n🗂️ **DOCUMENT GROUP: {source_name}**\n{'═' * 80}\n"
            group_content = []
            
            for doc in source_docs:
                doc.metadata["index"] = global_index
                doc.metadata["group"] = source_name
                group_content.append(format_document(doc, document_prompt))
                global_index += 1
            
            group_footer = f"\n{'═' * 80}\n**END OF {source_name}**\n"
            formatted_groups.append(group_header + document_separator.join(group_content) + group_footer)
        
        return "\n\n🔄 **SWITCHING TO NEXT SOURCE** 🔄\n".join(formatted_groups)
    
    else:
        # Single source - use standard format with enhanced metadata
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


def validate_source_attribution(answer: str, sources: list) -> dict:
    """
    Validate that the answer properly attributes information to sources.
    Returns suggestions for improvement if attribution is weak.
    """
    import re
    
    # Check for source references in the answer
    source_references = re.findall(r'[Ss]ource\s+(\d+)', answer)
    source_files = re.findall(r'[Ss]ource\s+\d+\s*\([^)]+\)', answer)
    
    validation_result = {
        "has_source_references": len(source_references) > 0,
        "source_count_mentioned": len(set(source_references)),
        "total_sources_available": len(sources),
        "has_file_attribution": len(source_files) > 0,
        "attribution_score": 0.0,
        "suggestions": []
    }
    
    # Calculate attribution score
    if len(sources) > 0:
        attribution_ratio = len(set(source_references)) / len(sources)
        file_attribution_bonus = 0.2 if validation_result["has_file_attribution"] else 0
        validation_result["attribution_score"] = min(attribution_ratio + file_attribution_bonus, 1.0)
    
    # Generate improvement suggestions
    if validation_result["attribution_score"] < 0.5:
        validation_result["suggestions"].append("Consider adding more explicit source references (e.g., 'According to Source 0...')")
    
    if not validation_result["has_file_attribution"]:
        validation_result["suggestions"].append("Include document names in source references (e.g., 'Source 1 (filename.pdf)')")
    
    if len(set(source_references)) < len(sources):
        validation_result["suggestions"].append(f"Not all sources were referenced. Available sources: {len(sources)}, Referenced: {len(set(source_references))}")
    
    return validation_result
