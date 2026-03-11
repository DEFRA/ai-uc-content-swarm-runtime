import pydantic_ai

import app.swarm.models as models

researcher_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@researcher_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    deps = ctx.deps

    return await deps.prompt_repository.get_prompt_by_name("researcher.md")
