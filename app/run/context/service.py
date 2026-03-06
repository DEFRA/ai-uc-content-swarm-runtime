import logging

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

        async with http_client.create_async_client(
            settings.cdp_uploader_timeout
        ) as client:
            resp = await client.post(
                f"{settings.cdp_uploader_base_url}/initiate",
                json={
                    "redirect": request.redirect,
                    "s3Bucket": settings.context_bucket,
                    "s3Path": run_id,
                    "callback": f"{settings.callback_base}/runs/{run_id}/contexts/callback",
                    "mimeTypes": ["text/plain"],
                    "metadata": {"run_id": run_id}
                },
            )

            resp.raise_for_status()

            data = api_schemas.CdpUploaderInitiateResponse(**resp.json())

            return models.UploadInitiation(
                upload_id=data.upload_id,
            )

    async def handle_upload_callback(
        self,
        payload: api_schemas.CdpUploaderStatusPayload,
        run_id: str | None = None,
    ) -> None:
        """Process and persist callback from uploader service.

        Args:
            payload: The callback payload from the uploader.
        """
        # Prefer explicit run_id passed via the callback path; fall back to metadata
        resolved_run_id = run_id or payload.metadata.get("run_id")

        if not resolved_run_id:
            msg = "Missing run_id in uploader callback metadata or path"
            raise ValueError(msg)

        contexts: list[models.ContextMetadata] = []

        for form_value in payload.form.values():
            if isinstance(form_value, api_schemas.FileUploadDetail):
                context = models.ContextMetadata(
                    id=form_value.file_id,
                    filename=form_value.filename,
                    s3_key=form_value.s3_key,
                    s3_bucket=form_value.s3_bucket,
                    content_type=form_value.content_type,
                    checksum_sha256=form_value.checksum_sha256,
                    status=form_value.file_status,
                )
                contexts.append(context)

        if contexts:
            await self.repository.append_contexts(resolved_run_id, contexts)
            logger.info("Added %d context(s) to run %s", len(contexts), resolved_run_id)
