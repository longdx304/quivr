import json
from typing import AsyncIterable
from uuid import UUID

from langchain.chains import ConversationalRetrievalChain, LLMChain
from langchain.chains.question_answering import load_qa_chain
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)
from langchain_core.prompts.prompt import PromptTemplate

from quivr_api.logger import get_logger
from quivr_api.modules.brain.knowledge_brain_qa import KnowledgeBrainQA
from quivr_api.modules.chat.dto.chats import ChatQuestion

logger = get_logger(__name__)


class BigBrain(KnowledgeBrainQA):
    """
    The BigBrain class integrates advanced conversational retrieval and language model chains
    to provide comprehensive and context-aware responses to user queries.

    It leverages a combination of document retrieval, question condensation, and document-based
    question answering to generate responses that are informed by a wide range of knowledge sources.
    """

    def __init__(
        self,
        **kwargs,
    ):
        """
        Initializes the BigBrain class with specific configurations.

        Args:
            **kwargs: Arbitrary keyword arguments.
        """
        super().__init__(
            **kwargs,
        )

    def get_chain(self):
        """
        Constructs and returns the conversational QA chain used by BigBrain.

        Returns:
            A ConversationalRetrievalChain instance.
        """
        system_template = """CRITICAL RESTRICTION: You can ONLY use the provided summaries to answer the user's question. DO NOT use external knowledge or general information.
        If the summaries do not contain the answer to the user's question, you MUST respond with exactly: "Brain không có thông tin cho câu hỏi trên. Vui lòng cung cấp thêm thông tin cho brain."
        Use markdown or any other techniques to display the content in a nice and aerated way. ALWAYS answer in Vietnamese (tiếng Việt), regardless of the language used in the question.
        Here are user instructions on how to respond: {custom_personality}
        ______________________
        {summaries}"""
        messages = [
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template("{question}"),
        ]
        CHAT_COMBINE_PROMPT = ChatPromptTemplate.from_messages(messages)

        ### Question prompt
        question_prompt_template = """CRITICAL RESTRICTION: Only use the following portion of a long document to answer the question. DO NOT use any external knowledge.
        If the text contains relevant information, return it verbatim in Vietnamese (tiếng Việt). If the answer is not in the text, respond with: "Brain không có thông tin cho câu hỏi trên. Vui lòng cung cấp thêm thông tin cho brain."
        {context}
        Question: {question}
        Relevant text, if any, else say Nothing:"""
        QUESTION_PROMPT = PromptTemplate(
            template=question_prompt_template, input_variables=["context", "question"]
        )

        ### Condense Question Prompt

        _template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question in Vietnamese (tiếng Việt), regardless of the original question's language.

        Chat History:
        {chat_history}
        Follow Up Input: {question}
        Standalone question in Vietnamese:"""
        CONDENSE_QUESTION_PROMPT = PromptTemplate.from_template(_template)

        api_base = None
        if self.brain_settings.ollama_api_base_url and self.model.startswith("ollama"):
            api_base = self.brain_settings.ollama_api_base_url

        llm = ChatLiteLLM(
            temperature=0,
            model=self.model,
            api_base=api_base,
            max_tokens=self.max_tokens,
        )

        retriever_doc = self.knowledge_qa.get_retriever()

        question_generator = LLMChain(llm=llm, prompt=CONDENSE_QUESTION_PROMPT)
        doc_chain = load_qa_chain(
            llm,
            chain_type="map_reduce",
            question_prompt=QUESTION_PROMPT,
            combine_prompt=CHAT_COMBINE_PROMPT,
        )

        chain = ConversationalRetrievalChain(
            retriever=retriever_doc,
            question_generator=question_generator,
            combine_docs_chain=doc_chain,
        )

        return chain

    async def generate_stream(
        self, chat_id: UUID, question: ChatQuestion, save_answer: bool = True
    ) -> AsyncIterable:
        """
        Generates a stream of responses for a given question in real-time.

        Args:
            chat_id (UUID): The unique identifier for the chat session.
            question (ChatQuestion): The question object containing the user's query.
            save_answer (bool): Flag indicating whether to save the answer to the chat history.

        Returns:
            An asynchronous iterable of response strings.
        """
        conversational_qa_chain = self.get_chain()
        transformed_history, streamed_chat_history = (
            self.initialize_streamed_chat_history(chat_id, question)
        )
        response_tokens = []

        async for chunk in conversational_qa_chain.astream(
            {
                "question": question.question,
                "chat_history": transformed_history,
                "custom_personality": (
                    self.prompt_to_use.content if self.prompt_to_use else None
                ),
            }
        ):
            if "answer" in chunk:
                response_tokens.append(chunk["answer"])
                streamed_chat_history.assistant = chunk["answer"]
                yield f"data: {json.dumps(streamed_chat_history.dict())}"

        self.save_answer(question, response_tokens, streamed_chat_history, save_answer)
