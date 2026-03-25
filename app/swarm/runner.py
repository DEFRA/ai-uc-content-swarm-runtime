import logging
from typing import Any, Protocol

import pydantic_ai

from app import config
from app.run.models import RunStatus
from app.swarm import llm, models
from app.swarm.agents import critic, manager, researcher, writer
from app.swarm.content_pages import repository as content_pages_repository
from app.swarm.context import repository as context_repository

logger = logging.getLogger(__name__)

settings = config.get_config()


class RunResultHandler(Protocol):
    """Protocol for status updates from swarm execution.

    Decouples the swarm domain from the run domain. RunService satisfies
    this contract without explicit inheritance. This handler receives status
    lifecycle updates as the run transitions through PENDING → RUNNING → COMPLETED/ERROR.
    """

    async def update_status(self, run_id: str, status: RunStatus) -> Any:
        """Update the status of a swarm run.

        Args:
            run_id: The ID of the run.
            status: The new RunStatus value.
        """
        ...


class SwarmRunner:
    def __init__(
        self,
        context_repository: context_repository.AbstractContextRepository,
        content_pages_repository: content_pages_repository.AbstractContentPagesRepository,
        result_handler: RunResultHandler,
    ) -> None:
        """Initialize SwarmRunner with required dependencies.

        Args:
            context_repository: Repository for loading context documents.
            content_pages_repository: Repository for persisting content pages.
            result_handler: Handler for storing run status results.
        """
        self.context_repository = context_repository
        self.content_pages_repository = content_pages_repository
        self.result_handler = result_handler

    def _get_active_agents(
        self,
    ) -> tuple[
        dict[models.AgentName, pydantic_ai.Agent[models.AgentDependencies, str]],
        models.ModelMapping,
    ]:
        """Define and return the active agents for the swarm."""
        active_agents: dict[
            models.AgentName, pydantic_ai.Agent[models.AgentDependencies, str]
        ] = {}
        llm_mapping = models.ModelMapping()

        active_agents[models.AgentName.MANAGER] = manager.manager_agent

        if settings.agent_feature_flags.researcher_enabled:
            active_agents[models.AgentName.RESEARCHER] = researcher.researcher_agent
            llm_mapping.append(models.AgentName.RESEARCHER, llm.claude_haiku)

        if settings.agent_feature_flags.critic_enabled:
            active_agents[models.AgentName.CRITIC] = critic.critic_agent
            llm_mapping.append(models.AgentName.CRITIC, llm.claude_sonnet)

        if settings.agent_feature_flags.writer_enabled:
            active_agents[models.AgentName.WRITER] = writer.writer_agent
            llm_mapping.append(models.AgentName.WRITER, llm.claude_sonnet)

        return active_agents, llm_mapping

    async def start_run(self, job: models.SwarmJob) -> str:
        """Starts a new swarm run with the given job."""
        active_agents, llm_mapping = self._get_active_agents()

        run_dependencies = models.AgentDependencies(
            run_config=job,
            context_repository=self.context_repository,
            group_chat=models.GroupChat(agents=active_agents),
            content_pages_repository=self.content_pages_repository,
            llm_mapping=llm_mapping,
        )

        run_usage = pydantic_ai.RunUsage()

        logger.info("Starting swarm run for run_id: %s", job.run_id)

        entry = await manager.manager_agent.run(
            "start",
            model=run_dependencies.get_model_for_agent(models.AgentName.MANAGER),
            usage=run_usage,
            usage_limits=pydantic_ai.UsageLimits(
                request_limit=settings.swarm_request_limit
            ),
            deps=run_dependencies,
        )

        logger.info("Run completed for run_id: %s", job.run_id)

        return entry.output

    async def handle_job(self, job: models.SwarmJob) -> None:
        """Process a swarm job from the queue with status orchestration.

        Args:
            job: The SwarmJob to process.

        Raises:
            Exception: If execution fails (after status is updated to ERROR).
        """
        logger.info("Handling swarm job for run %s", job.run_id)
        logger.info(
            "Starting swarm execution for run %s with task: %s",
            job.run_id,
            job.task,
        )

        await self.result_handler.update_status(job.run_id, RunStatus.RUNNING)

        try:
            await self.start_run(job)

            logger.info("Swarm execution completed for run %s", job.run_id)

            await self.result_handler.update_status(job.run_id, RunStatus.COMPLETED)

            logger.info("Status updated to COMPLETED for run %s", job.run_id)
        except Exception as e:
            logger.error("Swarm execution failed for run %s: %s", job.run_id, e)
            await self.result_handler.update_status(job.run_id, RunStatus.ERROR)
            raise
