import pydantic_ai

from app.swarm import llm
from app.swarm.agents import manager


class SwarmRunner:
    async def start_run(self, task: str) -> str:
        """Starts a new swarm run with the given task."""
        run_usage: pydantic_ai.RunUsage = pydantic_ai.RunUsage()

        entry = await manager.manager_agent.run(
            task,
            model=llm.claude_haiku,
            usage=run_usage,
        )

        return entry.output
    
    async def resume_run(self) -> str:
        """Resumes a paused swarm run with the given run ID."""

        raise NotImplementedError("Run resumption is not yet implemented.")
