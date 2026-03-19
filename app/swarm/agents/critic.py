import logging

import pydantic_ai

import app.swarm.content_pages.tools as content_page_tools
import app.swarm.models as models

logger = logging.getLogger(__name__)

critic_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@critic_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    logger.info("[Tool Call] Critic agent: get_instructions called")
    return await ctx.deps.prompt_repository.get_prompt_by_name("critic.md")


@critic_agent.tool
async def list_pages(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the keys of all content pages available for review."""
    logger.info("[Tool Call] Critic agent: list_pages called")
    return content_page_tools.list_pages(ctx.deps)


@critic_agent.tool
async def read_page(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], page_key: str
) -> str:
    """Read the current content of a content page for review.

    Args:
        page_key: The key of the page to read (e.g. 'main', 'sub/related').
    """
    logger.info("[Tool Call] Critic agent: read_page called")
    return content_page_tools.read_page(ctx.deps, page_key)


@critic_agent.tool
async def list_style_guide_documents(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content style guide rules available in the context store.

    Returns a JSON array of objects with title, description, and file fields.
    Use the file value with get_document_content to retrieve the full content of the rule.
    """
    logger.info("[Tool Call] Critic agent: list_style_guide_documents called")
    return await ctx.deps.context_repository.get_context(
        "content-style-guide/index.json"
    )


@critic_agent.tool
async def get_document_content(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], file: str
) -> str:
    """Retrieve the full content of a GOV.UK context document by its file path.

    Use the file path returned by list_style_guide_documents.
    """
    logger.info("[Tool Call] Critic agent: get_document_content called")
    try:
        return await ctx.deps.context_repository.get_context(file)
    except Exception as e:
        return f"Error retrieving document content for file '{file}': {str(e)}"
