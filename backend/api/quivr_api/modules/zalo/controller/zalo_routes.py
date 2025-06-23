from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse
from uuid import UUID
from quivr_api.logger import get_logger
from quivr_api.middlewares.auth import AuthBearer, get_current_user
from quivr_api.modules.user.entity.user_identity import UserIdentity
from quivr_api.modules.zalo.service.zalo_service import ZaloService

zalo_router = APIRouter()
logger = get_logger(__name__)
zalo_service = ZaloService()

@zalo_router.post("/zalo-webhook")
async def zalo_webhook(request: Request):
    data = await request.json()
    logger.info("Zalo webhook received with data:")
    logger.info(f"Request data: {data}")

    return {"message": "Zalo webhook received", "data": data}

@zalo_router.post("/zalo-webhook/oa")
async def zalo_webhook_oa(request: Request):
    data = await request.json()
    logger.info("Zalo webhook received with data:")
    logger.info(f"Request data: {data}")
    return {"message": "Zalo webhook oa", "data": data}

@zalo_router.get("/zalo_verifierIzkT0g7t6Y1LWhyVYBO5Ht-vrH2JpmD9CZ4v.html", response_class=HTMLResponse)
async def zalo_verification():
    """
    Zalo platform site verification endpoint.
    Returns an HTML page with the verification meta tag.
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta property="zalo-platform-site-verification" content="IzkT0g7t6Y1LWhyVYBO5Ht-vrH2JpmD9CZ4v" />
        <title>Zalo Platform Verification</title>
    </head>
    <body>
        <h1>Zalo Platform Verification</h1>
        <p>This page is used for Zalo platform verification.</p>
    </body>
    </html>
    """
    logger.info("Zalo verification page accessed")
    return html_content


@zalo_router.post("/zalo/integrate-brain/{brain_id}", dependencies=[Depends(AuthBearer())])
async def integrate_brain_with_zalo(
    brain_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
):
    """
    Integrate a specific brain with Zalo by updating the zalo_settings table
    """
    try:
        result = zalo_service.update_zalo_brain_integration(brain_id)
        
        if result["success"]:
            logger.info(f"Brain {brain_id} integrated with Zalo for user {current_user.email}")
            return {
                "message": "Brain successfully integrated with Zalo",
                "brain_id": str(brain_id),
                "success": True,
            }
        else:
            logger.error(f"Failed to integrate brain {brain_id} with Zalo: {result['message']}")
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error integrating brain {brain_id} with Zalo: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@zalo_router.get("/zalo/brain-integration/{brain_id}", dependencies=[Depends(AuthBearer())])
async def get_brain_zalo_integration(
    brain_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
):
    """
    Get Zalo integration status for a specific brain
    """
    try:
        integration = zalo_service.get_zalo_brain_integration(brain_id)
        
        return {
            "brain_id": str(brain_id),
            "integrated": integration is not None,
            "integration_data": integration,
        }
        
    except Exception as e:
        logger.error(f"Error getting Zalo integration for brain {brain_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@zalo_router.delete("/zalo/integrate-brain/{brain_id}", dependencies=[Depends(AuthBearer())])
async def remove_brain_zalo_integration(
    brain_id: UUID,
    current_user: UserIdentity = Depends(get_current_user),
):
    """
    Remove Zalo integration for a specific brain
    """
    try:
        result = zalo_service.remove_zalo_brain_integration(brain_id)
        
        if result["success"]:
            logger.info(f"Zalo integration removed for brain {brain_id} by user {current_user.email}")
            return {
                "message": "Zalo integration removed successfully",
                "brain_id": str(brain_id),
                "success": True,
            }
        else:
            logger.error(f"Failed to remove Zalo integration for brain {brain_id}: {result['message']}")
            raise HTTPException(status_code=500, detail=result["message"])
            
    except Exception as e:
        logger.error(f"Error removing Zalo integration for brain {brain_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


