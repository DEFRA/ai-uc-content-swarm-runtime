import pydantic_ai

import app.swarm.models as models
from app import config
from app.swarm.agents import researcher

settings = config.get_config()

sub_agent_toolset: pydantic_ai.FunctionToolset[models.AgentDependencies] = (
    pydantic_ai.FunctionToolset()
)

if settings.agent_feature_flags.researcher_enabled:
    sub_agent_toolset.add_function(researcher.ask_researcher_agent)

manager_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
    toolsets=[sub_agent_toolset],
)


@manager_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    deps = ctx.deps

    return await deps.prompt_repository.get_prompt_by_name("manager.md")
