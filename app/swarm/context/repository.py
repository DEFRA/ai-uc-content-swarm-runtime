import asyncio
import logging
from abc import ABC, abstractmethod

import types_boto3_s3

logger = logging.getLogger(__name__)


class ContextRepositoryError(Exception):
    """Generic repository error."""


class ContextNotFoundError(ContextRepositoryError):
    """Raised when a context document is not found."""


class AbstractContextRepository(ABC):
    """Abstract repository for loading context documents."""

    @abstractmethod
    async def get_context(self, key: str) -> str:
        """Retrieve a single context document by key.

        Args:
            key: The document key/identifier.

        Returns:
            The content of the context document.

        Raises:
            ContextRepositoryError: If retrieval fails.
        """


class S3ContextRepository(AbstractContextRepository):
    """S3-backed repository for context documents.

    Uses an injected boto3 S3 client with a ThreadPoolExecutor for non-blocking
    access from asyncio code.
    """

    def __init__(self, s3_client: types_boto3_s3.S3Client, bucket: str) -> None:
        """Initialize S3 repository.

        Args:
            s3_client: Injected boto3 S3 client.
            bucket: S3 bucket name. If None, uses CONTEXT_BUCKET from config.
        """
        self.client = s3_client
        self.bucket = bucket

    def _get_object(self, key: str) -> str:
        """Synchronous helper to get a context document from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read().decode("utf-8")
        except self.client.exceptions.NoSuchKey as err:
            msg = f"Context document not found: {key}"
            raise ContextNotFoundError(msg) from err
        except Exception as err:
            msg = f"Failed to get context from S3: {err}"
            raise ContextRepositoryError(msg) from err

    async def get_context(self, key: str) -> str:
        """Retrieve a context document from S3.

        Args:
            key: The S3 object key (e.g., "policy/document.txt").

        Returns:
            The content of the context document.

        Raises:
            ContextNotFoundError: If the document is not found.
            ContextRepositoryError: If retrieval fails.
        """

        return await asyncio.to_thread(self._get_object, key)
