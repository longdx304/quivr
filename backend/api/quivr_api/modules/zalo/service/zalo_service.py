from uuid import UUID
from typing import Optional
from quivr_api.logger import get_logger
from quivr_api.modules.dependencies import get_supabase_client

logger = get_logger(__name__)


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
