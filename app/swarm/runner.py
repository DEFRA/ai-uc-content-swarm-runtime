import pydantic_ai

from app.swarm import llm, models
from app.swarm.agents import manager
from app.swarm.context.repository import AbstractContextRepository


class SwarmRunner:
    def __init__(self, context_repository: AbstractContextRepository) -> None:
        """Initialize SwarmRunner with a context repository.

        Args:
            context_repository: Repository for loading context documents.
        """
        self.context_repository = context_repository

    async def start_run(self, config: models.RunConfig) -> str:
        """Starts a new swarm run with the given configuration."""

        run_dependencies = models.AgentDependencies(
            run_config=config, context_repository=self.context_repository
        )

        llm_mapping = run_dependencies.llm_mapping

        llm_mapping.append("manager", llm.claude_haiku)
        llm_mapping.append("researcher", llm.claude_haiku)

        run_usage: pydantic_ai.RunUsage = pydantic_ai.RunUsage()

        print(f"Starting swarm run with config: {config}")

        entry = await manager.manager_agent.run(
            config.task,
            model=run_dependencies.get_model_for_agent("manager"),
            usage=run_usage,
            deps=run_dependencies,
        )

        return entry.output
