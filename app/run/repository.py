import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime

import bson
import pymongo.asynchronous.database

import app.run.models as models
from app.run.context import models as context_models

logger = logging.getLogger(__name__)


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
    async def update_run(self, run_id: str, run: models.Run) -> None:
        """Update a run with new state.

        Updates the status, result, and/or contexts. For each context in the run,
        if a context with the same id exists in the database, it is updated;
        otherwise it is appended.

        Args:
            run_id: The ID of the run.
            run: The Run domain model with updated state.
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
        result = await self.collection.insert_one(run.to_document())

        return models.Run(
            id=str(result.inserted_id),
            name=run.name,
            status=run.status,
            result=run.result,
            created_at=run.created_at,
            updated_at=run.updated_at,
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

        run = models.Run(
            id=str(doc["_id"]),
            name=doc["name"],
            status=models.RunStatus(doc["status"]),
            result=doc.get("result"),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
        )

        for ctx_doc in doc.get("contexts", []):
            ctx_id: uuid.UUID = ctx_doc["id"]

            cdp_uploader = None
            if "cdpUploader" in ctx_doc:
                cdp_doc = ctx_doc["cdpUploader"]
                cdp_uploader = context_models.CdpUploaderMetadata(
                    s3_bucket=cdp_doc["s3Bucket"],
                    upload_id=cdp_doc.get("uploadId"),
                    s3_key=cdp_doc.get("s3Key"),
                    checksum_sha256=cdp_doc.get("checksumSha256"),
                    filename=cdp_doc.get("filename"),
                    status=cdp_doc.get("status", "pending"),
                )

            context = context_models.ContextMetadata(
                id=ctx_id,
                title=ctx_doc["title"],
                created_at=ctx_doc["created_at"],
                description=ctx_doc.get("description"),
                cdp_uploader=cdp_uploader,
            )

            run.add_context(context)

        return run

    async def update_run(self, run_id: str, run: models.Run) -> None:
        """Update a run with new state.

        Updates the status, result, and/or contexts. For each context in the run,
        if a context with the same id exists in the database, it is updated;
        otherwise it is appended.

        Args:
            run_id: The ID of the run.
            run: The Run domain model with updated state.
        """
        oid = bson.ObjectId(run_id)

        update_doc = {
            "status": run.status.value,
            "updated_at": datetime.now(tz=UTC),
        }

        if run.result is not None:
            update_doc["result"] = run.result

        await self.collection.update_one(
            {"_id": oid},
            {"$set": update_doc},
        )

        for ctx in run.contexts:
            context_doc: dict = {
                "id": ctx.id,
                "title": ctx.title,
                "created_at": ctx.created_at,
            }

            if ctx.description is not None:
                context_doc["description"] = ctx.description

            if ctx.cdp_uploader is not None:
                context_doc["cdpUploader"] = {
                    "s3Bucket": ctx.cdp_uploader.s3_bucket,
                    "uploadId": ctx.cdp_uploader.upload_id,
                    "s3Key": ctx.cdp_uploader.s3_key,
                    "checksumSha256": ctx.cdp_uploader.checksum_sha256,
                    "filename": ctx.cdp_uploader.filename,
                    "status": ctx.cdp_uploader.status,
                }

            result = await self.collection.update_one(
                {"_id": oid, "contexts.id": ctx.id},
                {"$set": {"contexts.$": context_doc}},
            )

            if result.modified_count == 0:
                await self.collection.update_one(
                    {"_id": oid},
                    {"$push": {"contexts": context_doc}},
                )
