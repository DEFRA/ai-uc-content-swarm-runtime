import logging

import pydantic_ai

import app.swarm.models as models
from app.swarm.toolsets.content_pages import content_pages_toolset
from app.swarm.toolsets.context_documents import context_documents_toolset

logger = logging.getLogger(__name__)

critic_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
    toolsets=[content_pages_toolset, context_documents_toolset],
)


@critic_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    logger.info("[Tool Call] Critic agent: get_instructions called")
    return await ctx.deps.prompt_repository.get_prompt_by_name("critic.md")
