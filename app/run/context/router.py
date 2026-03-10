import logging
import uuid
from typing import Annotated

import fastapi

from app.run import dependencies as run_dependencies
from app.run import models as run_models
from app.run import service as run_service
from app.run.context import api_schemas
from app.run.context import dependencies as context_dependencies
from app.run.context import service as context_service_module

router = fastapi.APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "/runs/{run_id}/contexts",
    status_code=fastapi.status.HTTP_201_CREATED,
    responses={
        fastapi.status.HTTP_201_CREATED: {
            "description": "Upload session initiated successfully",
        },
        fastapi.status.HTTP_404_NOT_FOUND: {
            "description": "Run not found for the given run_id",
        },
    },
)
async def initiate_context_upload(
    run_id: str,
    payload: api_schemas.ContextUploadRequest,
    context_service: Annotated[
        context_service_module.ContextService,
        fastapi.Depends(context_dependencies.get_context_service),
    ],
) -> dict:
    """Initiate a context/file upload session for a run."""
    try:
        upload = await context_service.initiate_upload(run_id, payload)
    except run_models.RunNotFoundError as e:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from e

    return {"upload_id": upload.upload_id}


@router.get(
    "/runs/{run_id}/contexts",
    status_code=fastapi.status.HTTP_200_OK,
    responses={
        fastapi.status.HTTP_200_OK: {
            "description": "List of context documents for the run"
        },
        fastapi.status.HTTP_204_NO_CONTENT: {
            "description": "Run found but no contexts available"
        },
        fastapi.status.HTTP_404_NOT_FOUND: {
            "description": "Run not found for the given run_id"
        },
    },
)
async def get_run_contexts(
    run_id: str,
    response: fastapi.Response,
    run_service: Annotated[
        run_service.RunService,
        fastapi.Depends(run_dependencies.get_run_service),
    ],
) -> list[api_schemas.ContextResponse]:
    """Get all context documents for a run."""
    run = await run_service.get_run(run_id)

    if not run:
        msg = f"Run with id {run_id} not found"
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND, detail=msg
        )

    if len(run.contexts) == 0:
        response.status_code = fastapi.status.HTTP_204_NO_CONTENT
        return []

    return [
        api_schemas.ContextResponse(
            id=ctx.id,
            filename=ctx.filename,
            title=ctx.title,
            s3_key=ctx.s3_key,
            s3_bucket=ctx.s3_bucket,
            checksum_sha256=ctx.checksum_sha256,
            status=ctx.status,
            created_at=ctx.created_at,
        )
        for ctx in run.contexts
    ]


@router.post("/runs/{run_id}/contexts/{context_id}/callback")
async def handle_callback(
    run_id: str,
    context_id: str,
    payload: api_schemas.CdpUploaderStatusPayload,
    context_service: Annotated[
        context_service_module.ContextService,
        fastapi.Depends(context_dependencies.get_context_service),
    ],
) -> None:
    """Handle callbacks from the uploader service.

    Parses the uploaded files from the callback and creates context entries in the run.

    Args:
        run_id: The run ID.
        context_id: The context_id path parameter to match and update the pending context.
        payload: The callback payload from the uploader.
        context_service: The context service.
    """
    await context_service.handle_upload_callback(
        payload, run_id=run_id, context_id=uuid.UUID(context_id)
    )
