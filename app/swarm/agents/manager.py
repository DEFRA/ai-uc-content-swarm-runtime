import pydantic_ai

import app.swarm.models as models
from app.swarm.agents import researcher

manager_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@manager_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    deps = ctx.deps

    return await deps.prompt_repository.get_prompt_by_name("manager.md")


@manager_agent.tool
async def ask_researcher_agent(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], question: str
) -> str:
    """Ask the researcher agent to analyze source material and surface evidence.

    Use this to ground the discussion in policy documents, user needs, and legislation.
    """

    response = await researcher.researcher_agent.run(
        question,
        deps=ctx.deps,
        usage=ctx.usage,
    )

    turn_number = len(ctx.deps.group_chat)

    exchange = models.AgentExchange(
        agent_name="Researcher",
        agent_role="researcher",
        question=question,
        response=response.output,
        turn_number=turn_number,
    )
    ctx.deps.group_chat.append(exchange)

    return f"[Researcher] {response.output}"
