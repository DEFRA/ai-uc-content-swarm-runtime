import pydantic_ai

from app.swarm import llm
from app.swarm.agents import manager


class SwarmRunner:
    async def run(self, task: str) -> str:
        run_usage: pydantic_ai.RunUsage = pydantic_ai.RunUsage()

        entry = await manager.manager_agent.run(
            task,
            model=llm.claude_haiku,
            usage=run_usage,
        )

        return entry.output
