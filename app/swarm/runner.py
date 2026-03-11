import pydantic_ai

from app.swarm import llm, models
from app.swarm.agents import manager


class SwarmRunner:
    async def start_run(self, task: str) -> str:
        """Starts a new swarm run with the given task."""

        run_dependencies = models.AgentDependencies()

        run_dependencies.llm_mapping.append("manager", llm.claude_haiku)
        run_dependencies.llm_mapping.append("researcher", llm.claude_haiku)

        run_usage: pydantic_ai.RunUsage = pydantic_ai.RunUsage()

        entry = await manager.manager_agent.run(
            task,
            model=run_dependencies.get_model_for_agent("manager"),
            usage=run_usage,
            deps=run_dependencies,
        )

        return entry.output
