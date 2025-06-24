import os
from uuid import UUID
from typing import Optional
from quivr_api.modules.chat.controller.chat.utils import RetrievalConfigPathEnv, get_config_file_path, load_and_merge_retrieval_configuration
from quivr_api.modules.models.entity.model import Model
from quivr_api.modules.rag_service.rag_service import RAGService
from quivr_api.modules.knowledge.service.knowledge_service import KnowledgeService
from quivr_api.modules.models.service.model_service import ModelService
from quivr_api.modules.vector.service.vector_service import VectorService
from quivr_api.modules.chat.dto.inputs import CreateChatProperties
from quivr_api.modules.chat.entity.chat import Chat
from quivr_api.modules.chat.service.chat_service import ChatService
from quivr_api.logger import get_logger
from quivr_api.modules.dependencies import get_supabase_client
from quivr_api.modules.brain.service.brain_service import BrainService
from quivr_api.modules.prompt.service.prompt_service import PromptService

logger = get_logger(__name__)
brain_service = BrainService()
prompt_service = PromptService()

class ZaloService:
    def __init__(self):
        self.db = get_supabase_client()

    def update_zalo_brain_integration(
        self, brain_id: UUID, refresh_token: Optional[str] = None
    ) -> dict:
        """
        Update or create Zalo integration for a specific brain
        """
        try:
            # Check if record exists
            existing_record = (
                self.db.table("zalo_settings")
                .select("*")
                .eq("zalo_brain_id", str(brain_id))
                .execute()
            )

            data = {
                "zalo_brain_id": str(brain_id),
                "zalo_app_refresh_token": refresh_token,
            }

            if existing_record.data:
                # Update existing record
                response = (
                    self.db.table("zalo_settings")
                    .update(data)
                    .eq("zalo_brain_id", str(brain_id))
                    .execute()
                )
                logger.info(f"Updated Zalo integration for brain {brain_id}")
            else:
                # Create new record
                response = (
                    self.db.table("zalo_settings")
                    .insert(data)
                    .execute()
                )
                logger.info(f"Created Zalo integration for brain {brain_id}")

            return {
                "success": True,
                "message": "Zalo integration updated successfully",
                "brain_id": str(brain_id),
            }

        except Exception as e:
            logger.error(f"Error updating Zalo integration for brain {brain_id}: {e}")
            return {
                "success": False,
                "message": f"Failed to update Zalo integration: {str(e)}",
                "brain_id": str(brain_id),
            }

    def get_zalo_brain_integration(self, brain_id: UUID) -> Optional[dict]:
        """
        Get Zalo integration settings for a specific brain
        """
        try:
            response = (
                self.db.table("zalo_settings")
                .select("*")
                .eq("zalo_brain_id", str(brain_id))
                .execute()
            )

            if response.data:
                return response.data[0]
            return None

        except Exception as e:
            logger.error(f"Error getting Zalo integration for brain {brain_id}: {e}")
            return None
    
    async def get_zalo_brain_id(self) -> Optional[str]:
        response = (
            self.db.table("zalo_settings")
            .select("*")
            .execute()

        )
        return response.data[0].get("zalo_brain_id")

    def remove_zalo_brain_integration(self, brain_id: UUID) -> dict:
        """
        Remove Zalo integration for a specific brain
        """
        try:
            response = (
                self.db.table("zalo_settings")
                .delete()
                .eq("zalo_brain_id", str(brain_id))
                .execute()
            )

            logger.info(f"Removed Zalo integration for brain {brain_id}")
            return {
                "success": True,
                "message": "Zalo integration removed successfully",
                "brain_id": str(brain_id),
            }

        except Exception as e:
            logger.error(f"Error removing Zalo integration for brain {brain_id}: {e}")
            return {
                "success": False,
                "message": f"Failed to remove Zalo integration: {str(e)}",
                "brain_id": str(brain_id),
            }
    
    async def create_zalo_chat(self, chat_service: ChatService, zalo_user_id: str) -> Chat:
        chat = await chat_service.create_zalo_chat(CreateChatProperties(name="Zalo Chat"), zalo_user_id)
        return chat
    
    async def get_model_by_name(self, model_name: str, model_service: ModelService) -> Model:
        model = await model_service.get_model(model_name)
        logger.info(f"Model 🔥: {model}")
        if model is None:
            model = await model_service.get_default_model()
            logger.info(f"Model 🔥: {model}")
        return model
    
    async def create_zalo_chat_question(self, chat_id: UUID, message: str, chat_service: ChatService, knowledge_service: KnowledgeService, model_service: ModelService, vector_service: VectorService) -> Chat | None:
        zalo_brain_id = await self.get_zalo_brain_id()
        logger.info(f"Zalo brain id: {zalo_brain_id}")
        brain = brain_service.get_brain_details(UUID(zalo_brain_id))

        assert brain is not None
        model = await self.get_model_by_name(str(brain.model), model_service)
        assert model is not None
        current_path = os.path.dirname(os.path.abspath(__file__))
        file_path = get_config_file_path(
                RetrievalConfigPathEnv.CHAT_WITH_LLM, current_path=current_path
            )
        retrieval_config = load_and_merge_retrieval_configuration(
                config_file_path=file_path, sqlmodel=model
            )
        service = RAGService(
                current_user=None,
                chat_id=chat_id,
                brain=brain,
                retrieval_config=retrieval_config,
                model_service=model_service,
                brain_service=brain_service,
                prompt_service=prompt_service,
                chat_service=chat_service,
                knowledge_service=knowledge_service,
                vector_service=vector_service,
            )
        chat_answer = await service.generate_answer(message)
        logger.info(f"Chat answer: {chat_answer}")
        return chat_answer