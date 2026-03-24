import logging
import uuid
from datetime import UTC, datetime

from app import config
from app.common import http_client
from app.run import models as run_models
from app.run import repository
from app.run.context import api_schemas, models

logger = logging.getLogger(__name__)

settings = config.get_config()


class ContextService:
    """Service for managing file uploads with the CDP uploader."""

    def __init__(self, run_repository: repository.RunRepository) -> None:
        """Initialize the service with a repository.

        Args:
            run_repository: The repository for run persistence.
        """
        self.repository = run_repository

    async def initiate_upload(
        self, run_id: str, request: api_schemas.ContextUploadRequest
    ) -> models.UploadInitiation:
        """Initiate a file upload session.

        Args:
            run_id: The run ID to associate with this upload session.
            request: Upload configuration from the client.

        Returns:
            UploadInitiation with the upload_id for the frontend to use.
        """
        run = await self.repository.get_run(run_id)

        if not run:
            error_message = f"Run with ID {run_id} not found"
            raise run_models.RunNotFoundError(error_message)

        context_id = uuid.uuid4()

        async with http_client.create_async_client(
            settings.cdp_uploader_timeout
        ) as client:
            resp = await client.post(
                f"{settings.cdp_uploader_base_url}/initiate",
                json={
                    "redirect": request.redirect,
                    "s3Bucket": settings.context_bucket,
                    "s3Path": f"{run_id}/policy",
                    "callback": f"{settings.callback_base}/runs/{run_id}/contexts/{str(context_id)}/callback",
                    "metadata": {"run_id": run_id},
                },
            )

            resp.raise_for_status()

            data = api_schemas.CdpUploaderInitiateResponse(**resp.json())

            pending_context = models.ContextMetadata(
                id=context_id,
                title=request.title,
                s3_bucket=settings.context_bucket,
                s3_key=None,
                checksum_sha256=None,
                status="pending",
                created_at=datetime.now(tz=UTC),
                description=request.description,
            )

            await self.repository.append_context(run_id, pending_context)

            logger.info(
                "Initiated upload session %s for run %s with context ID %s",
                data.upload_id,
                run.id,
                pending_context.id,
            )

            return models.UploadInitiation(
                upload_id=data.upload_id,
            )

    async def handle_upload_callback(
        self,
        payload: api_schemas.CdpUploaderStatusPayload,
        run_id: str,
        context_id: uuid.UUID,
    ) -> None:
        """Process and persist callback from uploader service.

        Args:
            payload: The callback payload from the uploader.
            run_id: The run ID.
            context_id: The context_id to match and update the pending context.
        """
        run = await self.repository.get_run(run_id)

        if run is None:
            msg = f"Run with ID {run_id} not found for uploader callback"
            raise run_models.RunNotFoundError(msg)

        pending_context = run.get_context(context_id)

        if pending_context:
            # Return as soon as first file upload detail is processed
            for form_value in payload.form.values():
                if isinstance(form_value, api_schemas.FileUploadDetail):
                    updated_context = models.ContextMetadata(
                        id=context_id,
                        title=pending_context.title,
                        s3_key=form_value.s3_key,
                        s3_bucket=form_value.s3_bucket,
                        checksum_sha256=form_value.checksum_sha256,
                        filename=form_value.filename,
                        status=form_value.file_status,
                        created_at=pending_context.created_at,
                        description=pending_context.description,
                    )

                    await self.repository.append_context(run.id, updated_context)

                    return
