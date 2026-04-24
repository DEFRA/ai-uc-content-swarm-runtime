import logging
import uuid
from datetime import UTC, datetime

from app import config
from app.common import http_client
from app.run import models as run_models
from app.run import repository
from app.run.context import api_schemas
from app.run.context import models as context_models

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
    ) -> context_models.UploadInitiation:
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

            cdp_uploader = context_models.CdpUploaderMetadata(
                s3_bucket=settings.context_bucket,
                upload_id=data.upload_id,
                status="pending",
            )

            pending_context = context_models.ContextMetadata(
                id=context_id,
                title=request.title,
                created_at=datetime.now(tz=UTC),
                description=request.description,
                cdp_uploader=cdp_uploader,
            )

            run.add_context(pending_context)

            await self.repository.update_run(run_id, run)

            logger.info(
                "Initiated upload session %s for run %s with context ID %s",
                data.upload_id,
                run.id,
                pending_context.id,
            )

            return context_models.UploadInitiation(
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

        if pending_context and pending_context.cdp_uploader:
            for form_value in payload.form.values():
                if isinstance(form_value, api_schemas.FileUploadDetail):
                    updated_cdp_uploader = context_models.CdpUploaderMetadata(
                        s3_bucket=form_value.s3_bucket,
                        upload_id=pending_context.cdp_uploader.upload_id,
                        s3_key=form_value.s3_key,
                        checksum_sha256=form_value.checksum_sha256,
                        filename=form_value.filename,
                        status=form_value.file_status,
                    )

                    updated_context = context_models.ContextMetadata(
                        id=context_id,
                        title=pending_context.title,
                        created_at=pending_context.created_at,
                        description=pending_context.description,
                        cdp_uploader=updated_cdp_uploader,
                    )

                    run.add_context(updated_context)
                    await self.repository.update_run(run.id, run)

                    return
