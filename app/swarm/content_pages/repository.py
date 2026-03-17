import asyncio
import logging
from abc import ABC, abstractmethod

import types_boto3_s3

logger = logging.getLogger(__name__)


class ContentPagesRepositoryError(Exception):
    """Generic content pages repository error."""


class ContentPageNotFoundError(ContentPagesRepositoryError):
    """Raised when a content page is not found."""


class AbstractContentPagesRepository(ABC):
    """Abstract repository for persisting run content pages."""

    @abstractmethod
    async def save_page(self, run_id: str, page_key: str, content: str) -> None:
        """Persist a content page."""

    @abstractmethod
    async def get_page(self, run_id: str, page_key: str) -> str:
        """Retrieve a content page by key."""

    @abstractmethod
    async def list_pages(self, run_id: str) -> list[str]:
        """List all page keys for a run."""


class S3ContentPagesRepository(AbstractContentPagesRepository):
    """S3-backed repository for content pages.

    Objects are stored at: runs/{run_id}/content-pages/{page_key}.md
    """

    _key_prefix = "content-pages"
    _md_suffix = ".md"

    def __init__(self, s3_client: types_boto3_s3.S3Client, bucket: str) -> None:
        self.client = s3_client
        self.bucket = bucket

    def _object_key(self, run_id: str, page_key: str) -> str:
        return f"runs/{run_id}/{self._key_prefix}/{page_key}{self._md_suffix}"

    def _page_key_from_object_key(self, run_id: str, object_key: str) -> str:
        prefix = f"runs/{run_id}/{self._key_prefix}/"
        return object_key.removeprefix(prefix).removesuffix(self._md_suffix)

    def _put_object(self, key: str, content: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="text/markdown",
            )
        except Exception as err:
            msg = f"Failed to save content page to S3: {err}"
            raise ContentPagesRepositoryError(msg) from err

    def _get_object(self, key: str) -> str:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except self.client.exceptions.NoSuchKey as err:
            msg = f"Content page not found: {key}"
            raise ContentPageNotFoundError(msg) from err
        except Exception as err:
            msg = f"Failed to get content page from S3: {err}"
            raise ContentPagesRepositoryError(msg) from err

    def _list_objects(self, prefix: str) -> list[str]:
        try:
            response = self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
            return [obj["Key"] for obj in response.get("Contents", [])]
        except Exception as err:
            msg = f"Failed to list content pages from S3: {err}"
            raise ContentPagesRepositoryError(msg) from err

    async def save_page(self, run_id: str, page_key: str, content: str) -> None:
        key = self._object_key(run_id, page_key)
        logger.info("Saving content page run_id=%s page_key=%s", run_id, page_key)
        await asyncio.to_thread(self._put_object, key, content)

    async def get_page(self, run_id: str, page_key: str) -> str:
        key = self._object_key(run_id, page_key)
        return await asyncio.to_thread(self._get_object, key)

    async def list_pages(self, run_id: str) -> list[str]:
        prefix = f"runs/{run_id}/{self._key_prefix}/"
        object_keys = await asyncio.to_thread(self._list_objects, prefix)
        return [self._page_key_from_object_key(run_id, k) for k in object_keys]
