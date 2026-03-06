from abc import ABC, abstractmethod
from logging import getLogger

from bson import ObjectId
from pymongo.asynchronous.database import AsyncDatabase

import app.run.models as models
from app.run.context.models import ContextMetadata

logger = getLogger(__name__)


class RunRepository(ABC):
    """Repository interface for run persistence and data access."""

    @abstractmethod
    async def create_run(self, run: models.Run) -> models.Run:
        """Create a new run record in the repository.

        Args:
            run: The Run domain model to create.

        Returns:
            The created Run record with assigned ID and timestamps.
        """

    @abstractmethod
    async def get_run(self, run_id: str) -> models.Run | None:
        """Retrieve a run by its ID.

        Args:
            run_id: The ID of the run to retrieve.

        Returns:
            The Run record if found, None otherwise.
        """

    @abstractmethod
    async def append_context(self, run_id: str, context: ContextMetadata) -> None:
        """Append a context document to a run.

        Args:
            run_id: The ID of the run.
            context: The ContextMetadata to append.
        """

    @abstractmethod
    async def append_contexts(
        self, run_id: str, contexts: list[ContextMetadata]
    ) -> None:
        """Append multiple context documents to a run.

        Args:
            run_id: The ID of the run.
            contexts: List of ContextMetadata to append.
        """


class MongoRunRepository(RunRepository):
    """MongoDB-backed implementation of RunRepository."""

    def __init__(self, db: AsyncDatabase) -> None:
        """Initialize the adapter with a MongoDB database.

        Args:
            db: The AsyncDatabase instance.
        """
        self.db = db
        self.collection = db["runs"]

    async def create_run(self, run: models.Run) -> models.Run:
        """Create a new run record in the repository.

        Args:
            run: The Run domain model to create.

        Returns:
            The created Run record with MongoDB-assigned ID.
        """

        result = await self.collection.insert_one(
            {
                "name": run.name,
                "status": run.status.value,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
                "contexts": [],
            }
        )

        return models.Run(
            id=str(result.inserted_id),
            name=run.name,
            status=run.status,
            created_at=run.created_at,
            updated_at=run.updated_at,
            contexts=[],
        )

    async def get_run(self, run_id: str) -> models.Run | None:
        """Retrieve a run by its ID.

        Args:
            run_id: The ID of the run to retrieve.

        Returns:
            The Run record if found, None otherwise.
        """
        doc = await self.collection.find_one({"_id": ObjectId(run_id)})

        if not doc:
            return None

        contexts = []
        for ctx_doc in doc.get("contexts", []):
            contexts.append(
                ContextMetadata(
                    id=ctx_doc["id"],
                    filename=ctx_doc["filename"],
                    s3_key=ctx_doc["s3_key"],
                    s3_bucket=ctx_doc["s3_bucket"],
                    content_type=ctx_doc["content_type"],
                    checksum_sha256=ctx_doc["checksum_sha256"],
                    status=ctx_doc.get("status", "uploaded"),
                    created_at=ctx_doc["created_at"],
                )
            )

        return models.Run(
            id=str(doc["_id"]),
            name=doc["name"],
            status=models.RunStatus(doc["status"]),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            contexts=contexts,
        )

    async def append_context(self, run_id: str, context: ContextMetadata) -> None:
        """Append a context document to a run.

        Args:
            run_id: The ID of the run.
            context: The ContextMetadata to append.
        """
        try:
            oid = ObjectId(run_id)
        except Exception:
            # Invalid ObjectId format
            return

        await self.collection.update_one(
            {"_id": oid},
            {
                "$push": {
                    "contexts": {
                        "id": context.id,
                        "filename": context.filename,
                        "s3_key": context.s3_key,
                        "s3_bucket": context.s3_bucket,
                        "content_type": context.content_type,
                        "checksum_sha256": context.checksum_sha256,
                        "status": context.status,
                        "created_at": context.created_at,
                    }
                }
            },
        )

    async def append_contexts(
        self, run_id: str, contexts: list[ContextMetadata]
    ) -> None:
        """Append multiple context documents to a run.

        Args:
            run_id: The ID of the run.
            contexts: List of ContextMetadata to append.
        """
        try:
            oid = ObjectId(run_id)
        except Exception:
            # Invalid ObjectId format
            return

        context_docs = [
            {
                "id": ctx.id,
                "filename": ctx.filename,
                "s3_key": ctx.s3_key,
                "s3_bucket": ctx.s3_bucket,
                "content_type": ctx.content_type,
                "checksum_sha256": ctx.checksum_sha256,
                "status": ctx.status,
                "created_at": ctx.created_at,
            }
            for ctx in contexts
        ]

        await self.collection.update_one(
            {"_id": oid},
            {"$push": {"contexts": {"$each": context_docs}}},
        )
