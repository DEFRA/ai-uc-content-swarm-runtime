import logging

import pydantic_ai

from app import config
from app.swarm import llm, models
from app.swarm.agents import manager, researcher, writer
from app.swarm.context.repository import AbstractContextRepository

logger = logging.getLogger(__name__)

settings = config.get_config()


class SwarmRunner:
    def __init__(self, context_repository: AbstractContextRepository) -> None:
        """Initialize SwarmRunner with a context repository.

        Args:
            context_repository: Repository for loading context documents.
        """
        self.context_repository = context_repository

    async def start_run(self, config: models.RunConfig) -> str:
        """Starts a new swarm run with the given configuration."""

        active_agents: dict[
            models.AgentName, pydantic_ai.Agent[models.AgentDependencies, str]
        ] = {}

        if settings.agent_feature_flags.researcher_enabled:
            active_agents[models.AgentName.RESEARCHER] = researcher.researcher_agent

        if settings.agent_feature_flags.writer_enabled:
            active_agents[models.AgentName.WRITER] = writer.writer_agent

        run_dependencies = models.AgentDependencies(
            run_config=config,
            context_repository=self.context_repository,
            group_chat=models.GroupChat(agents=active_agents),
        )

        llm_mapping = run_dependencies.llm_mapping
        llm_mapping.append("manager", llm.claude_haiku)

        if settings.agent_feature_flags.researcher_enabled:
            llm_mapping.append(models.AgentName.RESEARCHER, llm.claude_haiku)

        if settings.agent_feature_flags.writer_enabled:
            llm_mapping.append(models.AgentName.WRITER, llm.claude_haiku)

        run_usage: pydantic_ai.RunUsage = pydantic_ai.RunUsage()

        logger.info("Starting swarm run for run_id: %s", config.id)

        entry = await manager.manager_agent.run(
            config.task,
            model=run_dependencies.get_model_for_agent("manager"),
            usage=run_usage,
            usage_limits=pydantic_ai.UsageLimits(
                request_limit=settings.swarm_request_limit
            ),
            deps=run_dependencies,
        )

        return entry.output
