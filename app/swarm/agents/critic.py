import logging

import pydantic_ai

import app.swarm.content_pages.tools as content_pages_tools
import app.swarm.context.tools as context_tools
import app.swarm.models as models

logger = logging.getLogger(__name__)

critic_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
    toolsets=[
        content_pages_tools.content_pages_toolset,
        context_tools.context_documents_toolset,
    ],
)


@critic_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    logger.info("[Tool Call] Critic agent: get_instructions called")
    return await ctx.deps.prompt_repository.get_prompt_by_name("critic.md")
