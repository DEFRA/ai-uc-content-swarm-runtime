import logging

from app import config
from app.common import http_client
from app.context import api_schemas, models

logger = logging.getLogger(__name__)

settings = config.get_config()


class ContextService:
    """Minimal service that builds domain models for uploads and callbacks."""

    async def initiate_upload(
        self, task_id: str, request: api_schemas.ContextUploadRequest
    ) -> models.UploadInitiation:
        async with http_client.create_async_client(
            settings.cdp_uploader_timeout
        ) as client:
            resp = await client.post(
                f"{settings.cdp_uploader_base_url}/initiate",
                json={
                    "redirect": request.redirect,
                    "s3Bucket": settings.context_bucket,
                    "s3Path": task_id,
                    "mimeTypes": ["text/plain"],
                },
            )

            resp.raise_for_status()

            data = api_schemas.CdpUploaderInitiateResponse(**resp.json())
            return models.UploadInitiation(
                upload_id=data.upload_id,
            )
