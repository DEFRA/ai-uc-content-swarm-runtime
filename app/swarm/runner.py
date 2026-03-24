import logging
import uuid
from typing import Any, Protocol

import pydantic_ai

from app import config
from app.run.models import RunStatus
from app.swarm import llm, models
from app.swarm.agents import critic, manager, researcher, writer
from app.swarm.content_pages.repository import AbstractContentPagesRepository
from app.swarm.context import models as context_models
from app.swarm.context.repository import AbstractContextRepository

logger = logging.getLogger(__name__)

settings = config.get_config()


class SwarmRunner:
    def __init__(
        self,
        context_repository: AbstractContextRepository,
        content_pages_repository: AbstractContentPagesRepository,
    ) -> None:
        """Initialize SwarmRunner with a context repository.

        Args:
            context_repository: Repository for loading context documents.
            content_pages_repository: Repository for persisting content pages.
        """
        self.context_repository = context_repository
        self.content_pages_repository = content_pages_repository

    async def start_run(self, config: models.RunConfig) -> str:
        """Starts a new swarm run with the given configuration."""

        active_agents: dict[
            models.AgentName, pydantic_ai.Agent[models.AgentDependencies, str]
        ] = {}

        if settings.agent_feature_flags.researcher_enabled:
            active_agents[models.AgentName.RESEARCHER] = researcher.researcher_agent

        if settings.agent_feature_flags.writer_enabled:
            active_agents[models.AgentName.WRITER] = writer.writer_agent

        if settings.agent_feature_flags.critic_enabled:
            active_agents[models.AgentName.CRITIC] = critic.critic_agent

        run_dependencies = models.AgentDependencies(
            run_config=config,
            context_repository=self.context_repository,
            group_chat=models.GroupChat(agents=active_agents),
            content_pages_repository=self.content_pages_repository,
        )

        llm_mapping = run_dependencies.llm_mapping
        llm_mapping.append("manager", llm.claude_haiku)

        if settings.agent_feature_flags.researcher_enabled:
            llm_mapping.append(models.AgentName.RESEARCHER, llm.claude_haiku)

        if settings.agent_feature_flags.writer_enabled:
            llm_mapping.append(models.AgentName.WRITER, llm.claude_sonnet)

        if settings.agent_feature_flags.critic_enabled:
            llm_mapping.append(models.AgentName.CRITIC, llm.claude_sonnet)

        run_usage: pydantic_ai.RunUsage = pydantic_ai.RunUsage()

        logger.info("Starting swarm run for run_id: %s", config.id)

        entry = await manager.manager_agent.run(
            "start",
            model=run_dependencies.get_model_for_agent("manager"),
            usage=run_usage,
            usage_limits=pydantic_ai.UsageLimits(
                request_limit=settings.swarm_request_limit
            ),
            deps=run_dependencies,
        )

        logger.info("Run completed for run_id: %s", config.id)

        return entry.output


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


class SwarmJobHandler:
    """Handles execution of swarm jobs from the queue."""

    def __init__(
        self,
        swarm_runner_instance: SwarmRunner,
        run_result_handler: RunResultHandler,
    ) -> None:
        """Initialize the job handler.

        Args:
            swarm_runner_instance: The SwarmRunner for executing swarms.
            run_result_handler: Handler for storing results (satisfies RunResultHandler protocol).
        """
        self.swarm_runner = swarm_runner_instance
        self.run_result_handler = run_result_handler

    async def handle_job(self, job: models.SwarmJob) -> None:
        """Process a swarm job from the queue.

        Args:
            job: The SwarmJob to process.

        Raises:
            Exception: If execution fails.
        """
        logger.info("Handling swarm job for run %s", job.run_id)

        run_config = models.RunConfig(
            task=job.task,
            id=job.run_id,
            name=job.name,
            context_documents=[
                context_models.ContextDocument(
                    id=uuid.UUID(doc["id"]),
                    type=context_models.ContextType.POLICY,
                    name=doc["name"],
                    description=doc.get("description"),
                    path=doc["path"],
                )
                for doc in job.context_documents
            ],
        )

        logger.info(
            "Starting swarm execution for run %s with task: %s",
            job.run_id,
            job.task,
        )

        await self.run_result_handler.update_status(job.run_id, RunStatus.RUNNING)

        try:
            await self.swarm_runner.start_run(run_config)

            logger.info("Swarm execution completed for run %s", job.run_id)

            await self.run_result_handler.update_status(job.run_id, RunStatus.COMPLETED)

            logger.info("Status updated to COMPLETED for run %s", job.run_id)
        except Exception as e:
            logger.error("Swarm execution failed for run %s: %s", job.run_id, e)
            await self.run_result_handler.update_status(job.run_id, RunStatus.ERROR)
            raise
