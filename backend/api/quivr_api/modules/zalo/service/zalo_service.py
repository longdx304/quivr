import os
import requests
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
            response = (
                self.db.table("zalo_settings")
                .update({"value": str(brain_id)})
                .eq("key", "zalo_brain_id")
                .execute()
            )

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
                .eq("key", "zalo_brain_id")
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
            .select("value")
            .eq("key", "zalo_brain_id")
            .execute()

        )
        return response.data[0].get("value") if response.data else None

    async def get_zalo_refresh_token(self) -> Optional[str]:
        response = (
            self.db.table("zalo_settings")
            .select("value")
            .eq("key", "zalo_app_refresh_token")
            .execute()
        )
        return response.data[0].get("value") if response.data else None

    def remove_zalo_brain_integration(self, brain_id: UUID) -> dict:
        """
        Remove Zalo integration for a specific brain
        """
        try:
            brain = self.get_zalo_brain_integration(brain_id)
            assert brain is not None
            response = (
                self.db.table("zalo_settings")
                .update({"value": None})
                .eq("key", "zalo_brain_id")
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
                RetrievalConfigPathEnv.RAG, current_path=current_path
            )
        retrieval_config = load_and_merge_retrieval_configuration(
                config_file_path=file_path, sqlmodel=model
            )
        logger.info(f"Brain service")
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
        logger.info(f"Service created")
        chat_answer = await service.generate_answer(message)
        logger.info(f"Chat answer: {chat_answer}")
        return chat_answer

    async def update_zalo_refresh_token(self, refresh_token: str) -> dict:
        """
        Update Zalo refresh token
        """
        try:
            response = (
                self.db.table("zalo_settings")
                .update({"value": str(refresh_token)})
                .eq("key", "zalo_app_refresh_token")
                .execute()
            )
            return {
                "success": True,
                "message": "Zalo refresh token updated successfully",
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update Zalo refresh token: {str(e)}",
            }
    
    async def get_zalo_token(self, code: str) -> dict:
        """
        Get Zalo access token using Zalo OAuth API
        """
        try:
            # Get app_id and secret_key from environment variables
            app_id = os.getenv("ZALO_APP_ID")
            secret_key = os.getenv("ZALO_SECRET_KEY")
            logger.info(f"App id: {app_id}")
            logger.info(f"Secret key: {secret_key}")
            
            if not app_id or not secret_key:
                return {
                    "success": False,
                    "message": "ZALO_APP_ID or ZALO_SECRET_KEY environment variables not set",
                }

            # Prepare headers according to Zalo API requirements
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "secret_key": secret_key,
            }

            # Prepare data payload
            data = {
                "code": code,
                "app_id": app_id,
                "grant_type": "authorization_code",
            }

            # Make request to Zalo OAuth API
            response = requests.post(
                "https://oauth.zaloapp.com/v4/oa/access_token",
                headers=headers,
                data=data,
            )

            # Check if request was successful
            if response.status_code == 200:
                response_data = response.json()
                
                return {
                    "success": True,
                    "data": response_data,
                }
            else:
                logger.error(f"Zalo API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Zalo API error: {response.status_code} - {response.text}",
                }

        except Exception as e:
            logger.error(f"Error getting Zalo access token: {e}")
            return {
                "success": False,
                "message": f"Failed to get Zalo access token: {str(e)}",
            }

    async def get_zalo_access_token(self, refresh_token: str) -> dict:
        """
        Get Zalo access token
        """
        try:
            # Get app_id and secret_key from environment variables
            app_id = os.getenv("ZALO_APP_ID")
            logger.info(f"App id: {app_id}")
            secret_key = os.getenv("ZALO_SECRET_KEY")
            logger.info(f"Secret key: {secret_key}")
            
            if not app_id or not secret_key:
                logger.error("ZALO_APP_ID or ZALO_SECRET_KEY environment variables not set")
                return {
                    "success": False,
                    "message": "ZALO_APP_ID or ZALO_SECRET_KEY environment variables not set", 
                }

            # Prepare headers according to Zalo API requirements
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "secret_key": secret_key,
            }

            # Prepare data payload
            data = {
                "refresh_token": refresh_token,
                "app_id": app_id,
                "grant_type": "refresh_token",
            }

            # Make request to Zalo OAuth API
            response = requests.post(
                "https://oauth.zaloapp.com/v4/oa/access_token",
                headers=headers,
                data=data,
            )

            # Check if request was successful
            if response.status_code == 200:
                response_data = response.json()
                await self.update_zalo_refresh_token(response_data["refresh_token"])
                return {
                    "success": True,
                    "access_token": response_data["access_token"],
                }
            else:
                logger.error(f"Zalo API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "message": f"Zalo API error: {response.status_code} - {response.text}",
                }

        except Exception as e:
            logger.error(f"Error getting Zalo access token: {e}")
            return {
                "success": False,
                "message": f"Failed to get Zalo access token: {str(e)}",
            }

    async def send_zalo_message(self, user_id: str, message: str) -> dict:
        """
        Send Zalo message
        """
        refresh_token = await self.get_zalo_refresh_token()
        logger.info(f"Refresh token: {refresh_token}")
        if refresh_token is None:
            logger.error("Refresh token not found")
            return {
                "success": False,
                "message": "Refresh token not found",
            }
        token = await self.get_zalo_access_token(refresh_token)
        logger.info(f"Access token: {token}")
        if not token["success"]:
            logger.error(f"Failed to get Zalo access token: {token['message']}")
            return {
                "success": False,
                "message": token["message"],
            }
        access_token = token["access_token"]
        headers = {
            "Content-Type": "application/json",
            "access_token": access_token,
        }

        data = {
            "recipient": {
                "user_id": user_id,
            },
            "message": {"text": message},
        }
        response = requests.post(
            "https://openapi.zalo.me/v3.0/oa/message/cs",
            headers=headers,
            json=data,
        )
        logger.info(f"Response: {response.json()}")

        if response.status_code == 200:
            logger.info(f"Zalo message sent successfully: {response.json()}")
            return {
                "success": True,
                "message": "Zalo message sent successfully",
                "data": response.json(),
            }
        else:
            logger.error(f"Zalo API error: {response.status_code} - {response.text}")
            logger.error(f"Zalo API error: {response.json()}")
            return {
                "success": False,
                "message": f"Zalo API error: {response.status_code} - {response.text}",
            }