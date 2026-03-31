from datetime import UTC, datetime
from logging import getLogger

import app.run.models as models
import app.run.repository as repository
import app.run.sqs_adapter as sqs_adapter

logger = getLogger(__name__)


class RunService:
    """Service that orchestrates run lifecycle and swarm execution."""

    def __init__(
        self,
        run_repository: repository.RunRepository,
        sqs: sqs_adapter.AbstractJobPublisher,
    ) -> None:
        """Initialize the service with a repository and job queue.

        Args:
            run_repository: The repository for run persistence.
            sqs: The job queue adapter instance.
        """
        self.repository = run_repository
        self.sqs = sqs

    async def setup_run(self, run: models.Run) -> models.Run:
        """Create a new run record without executing it.

        Args:
            run: The Run domain model.

        Returns:
            The created Run record with status=pending.
        """

        run = await self.repository.create_run(run)

        logger.info("Created run %s", run.id)

        return run

    async def start_run(self, run_id: str) -> models.Run:
        """Start a run by publishing a job to the SQS queue.

        Updates the run status to PENDING and publishes to the queue. The task
        can override the run's existing task if provided.

        Args:
            run_id: The ID of the run to start.
            task: Optional task to override the run's task.

        Returns:
            The updated Run record with status=PENDING.

        Raises:
            RunNotFoundError: If the run does not exist.
        """
        run = await self.repository.get_run(run_id)

        if not run:
            msg = f"Run with ID {run_id} not found"
            raise models.RunNotFoundError(msg)

        context_documents = [
            {
                "id": str(ctx.id),
                "name": ctx.title,
                "description": ctx.title,
                "path": ctx.s3_key,
            }
            for ctx in run.contexts
        ]

        job = sqs_adapter.SwarmRunJob(
            run_id=run.id,
            name=run.name,
            context_documents=context_documents,
        )

        await self.sqs.publish_job(job)

        await self.update_status(run.id, models.RunStatus.PENDING)

        logger.info("Published run job %s to queue", run.id)

        return run

    async def update_status(self, run_id: str, status: models.RunStatus) -> models.Run:
        """Update the status of a run.

        Args:
            run_id: The ID of the run.
            status: The new RunStatus value.

        Returns:
            The updated Run record.

        Raises:
            RunNotFoundError: If the run does not exist.
        """
        run = await self.repository.get_run(run_id)

        if not run:
            msg = f"Run with ID {run_id} not found"
            raise models.RunNotFoundError(msg)

        run.status = status
        run.updated_at = datetime.now(tz=UTC)

        await self.repository.update_status(run.id, status)

        logger.info("Updated run %s status to %s", run.id, status.value)

        return run

    async def store_result(self, run_id: str, result: str) -> models.Run:
        """Store the result of a completed swarm run.

        Args:
            run_id: The ID of the run.
            result: The output result from the swarm execution.

        Returns:
            The updated Run record.

        Raises:
            RunNotFoundError: If the run does not exist.
        """
        run = await self.repository.get_run(run_id)

        if not run:
            msg = f"Run with ID {run_id} not found"
            raise models.RunNotFoundError(msg)

        run.result = result
        run.status = models.RunStatus.COMPLETED
        run.updated_at = datetime.now(tz=UTC)

        await self.repository.update_run_result(run.id, result)

        logger.info("Stored result for run %s", run.id)

        return run

    async def get_run(self, run_id: str) -> models.Run | None:
        """Retrieve a run by its ID.

        Args:
            run_id: The ID of the run to retrieve.

        Returns:
            The Run record if found, None otherwise.
        """
        return await self.repository.get_run(run_id)
