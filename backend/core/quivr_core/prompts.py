import datetime

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.prompts.base import BasePromptTemplate
from pydantic import ConfigDict, create_model


class CustomPromptsDict(dict):
    def __init__(self, type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._type = type

    def __setitem__(self, key, value):
        # Automatically convert the value into a tuple (my_type, value)
        super().__setitem__(key, (self._type, value))


def _define_custom_prompts() -> CustomPromptsDict:
    custom_prompts: CustomPromptsDict = CustomPromptsDict(type=BasePromptTemplate)

    today_date = datetime.datetime.now().strftime("%B %d, %Y")

    # ---------------------------------------------------------------------------
    # Prompt for question rephrasing - Enhanced for better context retention
    # ---------------------------------------------------------------------------
    _template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.

    Important instructions:
    1. Maintain all specific details, entity names, numerical values, and technical terms from the follow-up question
    2. Incorporate relevant context from the chat history that is necessary to understand the question
    3. Make sure the rephrased question contains all information needed to provide a complete answer
    4. Keep the original intent and scope of the question intact
    5. Preserve the original language of the question

    Chat History:
    {chat_history}
    
    Follow Up Input: {question}
    
    Standalone question:"""

    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)
    custom_prompts["CONDENSE_QUESTION_PROMPT"] = CONDENSE_QUESTION_PROMPT

    # ---------------------------------------------------------------------------
    # Prompt for RAG - Improved for more detailed and accurate answers
    # ---------------------------------------------------------------------------
    system_message_template = (
        f"Your name is MedzavyBot. You're a helpful assistant specialized in providing detailed, accurate information based on document analysis. Today's date is {today_date}."
    )

    system_message_template += """
    ## Response Guidelines:
    - Provide comprehensive, detailed answers based on the context provided from the documents
    - Include specific data points, figures, quotes, and exact information from the context
    - Format your response using markdown for readability:
        - Use headings (##, ###) to organize complex answers
        - Use **bold** for important concepts
        - Use *italics* for emphasis
        - Use bullet points or numbered lists for multiple items
        - Use `code blocks` for any technical content, formulas, or code snippets
    - Be precise about what the documents actually state - distinguish between explicit information and inferences
    - When the documents provide numerical data, always include these exact figures
    - If information appears in multiple documents, synthesize it for completeness
    - If documents contradict each other, acknowledge this and explain the different perspectives
    - If the answer is not contained in the provided context, clearly state "Based on the provided documents, I cannot answer this question" and explain what information is missing
    - Never fabricate information or citations not present in the provided context
    - Answer in the same language as the user's question
    
    You have access to the following files to answer the user question (limited to first 20 files):
    {files}

    If not None, follow these additional user instructions when answering: {custom_instructions}
    """

    template_answer = """
    ## Context Information:
    {context}

    ## User Question: 
    {question}
    
    ## Detailed Answer:
    """

    RAG_ANSWER_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            HumanMessagePromptTemplate.from_template(template_answer),
        ]
    )
    custom_prompts["RAG_ANSWER_PROMPT"] = RAG_ANSWER_PROMPT

    # ---------------------------------------------------------------------------
    # Prompt for formatting documents - Enhanced for better context representation
    # ---------------------------------------------------------------------------
    DEFAULT_DOCUMENT_PROMPT = PromptTemplate.from_template(
        template="Source: {index} \n {page_content}"
    )
    custom_prompts["DEFAULT_DOCUMENT_PROMPT"] = DEFAULT_DOCUMENT_PROMPT

    # ---------------------------------------------------------------------------
    # Prompt for chatting directly with LLMs - Enhanced for more detailed responses
    # ---------------------------------------------------------------------------
    system_message_template = (
        f"Your name is MedzavyBot. You're a helpful assistant trained to provide detailed, accurate, and relevant information. Today's date is {today_date}."
    )
    system_message_template += """
    ## Response Guidelines:
    - Provide thorough and specific answers to user questions
    - Use markdown formatting to structure your responses:
        - Use headings to organize complex information
        - Use bold and italic text for emphasis
        - Use bullet points or numbered lists for multiple items
        - Use code blocks with appropriate syntax highlighting for code
    - When analyzing problems, break them down into components and explain step-by-step
    - When discussing concepts, include examples and practical applications
    - Respond in the same language as the user's question
    - Be accurate and precise - avoid making claims without sufficient basis
    - When uncertain, acknowledge the limitations of your knowledge
    
    If not None, also follow these user instructions when answering: {custom_instructions}
    """

    template_answer = """
    ## User Question:
    {question}
    
    ## Detailed Answer:
    """
    
    CHAT_LLM_PROMPT = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(system_message_template),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessagePromptTemplate.from_template(template_answer),
        ]
    )
    custom_prompts["CHAT_LLM_PROMPT"] = CHAT_LLM_PROMPT

    return custom_prompts


_custom_prompts = _define_custom_prompts()
CustomPromptsModel = create_model(
    "CustomPromptsModel", **_custom_prompts, __config__=ConfigDict(extra="forbid")
)

custom_prompts = CustomPromptsModel()