import uuid
from abc import ABC, abstractmethod
from logging import getLogger

import bson
import pymongo.asynchronous.database

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
    async def append_context(
        self, run_id: str, context: ContextMetadata | list[ContextMetadata]
    ) -> None:
        """Append one or more context documents to a run.

        For each provided context: if a context with the same id exists in the run,
        it is updated; otherwise it is appended.

        Args:
            run_id: The ID of the run.
            context: A ContextMetadata or list of ContextMetadata to append/upsert.
        """


class MongoRunRepository(RunRepository):
    """MongoDB-backed implementation of RunRepository."""

    def __init__(self, db: pymongo.asynchronous.database.AsyncDatabase) -> None:
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
        doc = await self.collection.find_one({"_id": bson.ObjectId(run_id)})

        if not doc:
            return None

        contexts = []
        for ctx_doc in doc.get("contexts", []):
            # Stored as BSON Binary UUID subtype; convert to Python UUID
            ctx_id = uuid.UUID(bytes=ctx_doc["id"])

            contexts.append(
                ContextMetadata(
                    id=ctx_id,
                    title=ctx_doc["title"],
                    s3_bucket=ctx_doc["s3_bucket"],
                    s3_key=ctx_doc.get("s3_key"),
                    checksum_sha256=ctx_doc.get("checksum_sha256"),
                    filename=ctx_doc.get("filename"),
                    status=ctx_doc.get("status", "uploaded"),
                    created_at=ctx_doc["created_at"],
                    description=ctx_doc.get("description"),
                )
            )
        # Build set of context IDs for O(1) membership checks from stored contexts
        context_ids_set = set()
        for ctx in contexts:
            context_ids_set.add(ctx.id)

        return models.Run(
            id=str(doc["_id"]),
            name=doc["name"],
            status=models.RunStatus(doc["status"]),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            contexts=contexts,
            context_ids=context_ids_set,
        )

    async def append_context(
        self, run_id: str, context: ContextMetadata | list[ContextMetadata]
    ) -> None:
        """Append one or more context documents to a run.

        For each provided context: if a context with the same id exists in the run,
        it is updated; otherwise it is appended.

        Args:
            run_id: The ID of the run.
            context: A ContextMetadata or list of ContextMetadata to append/upsert.
        """
        try:
            oid = bson.ObjectId(run_id)
        except Exception:
            # Invalid ObjectId format
            return

        # Normalize to list
        contexts = [context] if isinstance(context, ContextMetadata) else context

        for ctx in contexts:
            # Store UUID as BSON Binary with UUID subtype
            ctx_id_binary = bson.Binary(ctx.id.bytes, subtype=4)

            context_doc = {
                "id": ctx_id_binary,
                "title": ctx.title,
                "s3_key": ctx.s3_key,
                "s3_bucket": ctx.s3_bucket,
                "checksum_sha256": ctx.checksum_sha256,
                "status": ctx.status,
                "created_at": ctx.created_at,
            }
            if ctx.filename is not None:
                context_doc["filename"] = ctx.filename
            if ctx.description is not None:
                context_doc["description"] = ctx.description

            # Try to update an existing context by id, or append if not found
            result = await self.collection.update_one(
                {"_id": oid, "contexts.id": ctx_id_binary},
                {"$set": {"contexts.$": context_doc}},
            )

            if result.modified_count == 0:
                # Context not found, append it
                await self.collection.update_one(
                    {"_id": oid},
                    {"$push": {"contexts": context_doc}},
                )
