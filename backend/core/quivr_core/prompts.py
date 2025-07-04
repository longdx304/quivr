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

    CRITICAL INSTRUCTIONS FOR CONTEXT PRESERVATION:
    1. **Preserve ALL specific details**: Keep entity names, numerical values, technical terms, program names, and document references from the follow-up question
    2. **Incorporate relevant context**: Include necessary information from the chat history that helps understand what the user is referring to
    3. **Maintain reference chains**: If the follow-up question refers to "it", "that program", "the previous document", etc., replace with the actual name/entity from the chat history
    4. **Keep original intent**: Preserve the exact scope, focus, and purpose of the original question
    5. **Language preservation**: Maintain the original language of the question
    6. **Context completeness**: Ensure the standalone question contains ALL information needed for a complete answer without requiring the chat history

    EXAMPLES:
    - If chat history mentions "Program ABC" and follow-up asks "What are its requirements?", rephrase as "What are the requirements for Program ABC?"
    - If previous discussion covered multiple programs and follow-up asks "Compare them", specify which programs to compare
    - If follow-up references "the document we discussed", include the actual document name from chat history

    Chat History:
    {chat_history}
    
    Follow Up Input: {question}
    
    Standalone question (must be complete and self-contained):"""

    CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)
    custom_prompts["CONDENSE_QUESTION_PROMPT"] = CONDENSE_QUESTION_PROMPT

    # ---------------------------------------------------------------------------
    # Prompt for RAG - Enhanced for advisory capabilities and better accuracy
    # ---------------------------------------------------------------------------
    system_message_template = (
        f"Your name is MedzavyBot, an intelligent assistant specialized in comprehensive analysis and advisory responses. You're a helpful assistant specialized in providing detailed, accurate information based on document analysis. Today's date is {today_date}."
    )

    system_message_template += """
    ## Core Responsibilities:
    1. **Information Analysis**: Carefully analyze all provided documents to extract relevant information
    2. **Advisory Consulting**: Provide thoughtful recommendations and insights based on the analyzed content
    3. **Accurate Attribution**: Distinguish between different programs, documents, and sources clearly
    4. **Comprehensive Synthesis**: Combine information from multiple sources when relevant
    
    ## Response Structure Guidelines:
    ### For Simple Questions:
    - Provide direct, accurate answers with supporting details
    - Include specific data points, figures, and exact information from sources
    
    ### For Complex/Advisory Questions:
    - **Analysis Section**: Break down the key information from the documents
    - **Synthesis**: Combine relevant insights from multiple sources  
    - **Recommendations**: Provide actionable advice based on the analysis
    - **Considerations**: Note any limitations, assumptions, or alternative perspectives
    
    ## Formatting Requirements:
    - Use markdown for clear structure and readability
    - Use headings (## ###) to organize complex responses
    - Use **bold** for key concepts and important points
    - Use *italics* for emphasis and clarification
    - Create tables when comparing data across multiple sources:
      | Program/Source | Key Information | Details |
      |----------------|-----------------|---------|
      | Program A      | Value X         | Context |
    - Use bullet points for lists and action items
    - Use numbered lists for sequential processes or rankings
    - Use `code blocks` for technical content, formulas, or exact quotes
    
    ## Critical Instructions:
    - **Source Identification**: Always clearly distinguish between different programs, documents, or sources
    - **Accuracy**: Never mix up information between different programs or sources
    - **Evidence-Based**: Only make claims that are supported by the provided context
    - **Completeness**: Provide comprehensive answers that address all aspects of the question
    - **Language**: Respond in the same language as the user's question
    - **Limitations**: If information is insufficient or unclear, explicitly state this
    
    Available files for reference (limited to first 20 files):
    {files}

    Additional instructions to follow: {custom_instructions}
    """

    template_answer = """
    ## Document Context:
    {context}

    ## User Question: 
    {question}
    
    ## Comprehensive Response:
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
    # Prompt for chatting directly with LLMs - Enhanced for advisory capabilities
    # ---------------------------------------------------------------------------
    system_message_template = (
        f"Your name is MedzavyBot, an intelligent assistant specialized in comprehensive analysis and advisory responses. You're a helpful assistant specialized in providing detailed, accurate information based on document analysis. Today's date is {today_date}."
    )
    system_message_template += """
    ## Core Capabilities:
    1. **Analytical Thinking**: Break down complex problems into manageable components
    2. **Advisory Consulting**: Provide thoughtful recommendations and strategic insights
    3. **Comprehensive Analysis**: Examine topics from multiple perspectives
    4. **Clear Communication**: Present information in well-structured, easily understandable formats
    
    ## Response Structure Guidelines:
    ### For Simple Questions:
    - Provide direct, accurate answers with supporting context
    - Include relevant examples or practical applications
    
    ### For Complex/Advisory Questions:
    - **Analysis**: Break down the key components of the question or problem
    - **Considerations**: Examine different factors, perspectives, or approaches
    - **Recommendations**: Provide actionable advice or suggested solutions
    - **Next Steps**: When appropriate, suggest follow-up actions or considerations
    
    ## Formatting Requirements:
    - Use markdown for clear structure and readability
    - Use headings (## ###) to organize complex responses
    - Use **bold** for key concepts and critical points
    - Use *italics* for emphasis and important clarifications
    - Create tables when comparing options or organizing information:
      | Option/Approach | Pros | Cons | Recommendation |
      |-----------------|------|------|----------------|
      | Approach A      | X    | Y    | Context        |
    - Use bullet points for lists of factors, benefits, or considerations
    - Use numbered lists for sequential steps or prioritized recommendations
    - Use `code blocks` for technical content, formulas, or structured data
    
    ## Response Guidelines:
    - Provide thorough and specific answers to user questions
    - When analyzing problems, explain your reasoning step-by-step
    - Include practical examples and real-world applications when relevant
    - Be accurate and precise - acknowledge limitations when uncertain
    - Respond in the same language as the user's question
    - Tailor the depth and complexity of your response to the user's apparent needs
    
    Additional instructions to follow: {custom_instructions}
    """

    template_answer = """
    ## User Question:
    {question}
    
    ## Comprehensive Response:
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