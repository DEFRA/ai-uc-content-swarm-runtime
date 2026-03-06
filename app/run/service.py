from logging import getLogger

import app.run.models as models
import app.run.repository as repository
import app.swarm.runner as swarm_runner

logger = getLogger(__name__)


class RunService:
    """Service that orchestrates run lifecycle and swarm execution."""

    def __init__(
        self, run_repository: repository.RunRepository, swarm: swarm_runner.SwarmRunner
    ) -> None:
        """Initialize the service with a repository and swarm runner.

        Args:
            run_repository: The repository for run persistence.
            swarm: The SwarmRunner instance.
        """
        self.repository = run_repository
        self.swarm = swarm

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

    async def get_run(self, run_id: str) -> models.Run | None:
        """Retrieve a run by its ID.

        Args:
            run_id: The ID of the run to retrieve.

        Returns:
            The Run record if found, None otherwise.
        """
        return await self.repository.get_run(run_id)
