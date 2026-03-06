import logging
from typing import Annotated

import fastapi

from app.context import api_schemas, dependencies, service

router = fastapi.APIRouter()

logger = logging.getLogger(__name__)


@router.post("/context/{task_id}/initiate")
async def initiate_upload(
    task_id: str,
    request: api_schemas.ContextUploadRequest,
    context_service: Annotated[
        service.ContextService, fastapi.Depends(dependencies.get_context_service)
    ],
) -> api_schemas.CdpUploaderInitiateResponse:
    """Initiate an upload by calling the upstream uploader service and returning the relevant info to the caller."""
    upload = await context_service.initiate_upload(task_id, request)

    return api_schemas.CdpUploaderInitiateResponse(
        uploadId=upload.upload_id,
    )


@router.post("/context/callback/{upload_id}")
def handle_callback(
    upload_id: str, payload: api_schemas.CdpUploaderStatusResponse
) -> None:
    """Handle callbacks from the uploader service."""
    logger.info("Received callback: %s with payload: %s", upload_id, payload)
