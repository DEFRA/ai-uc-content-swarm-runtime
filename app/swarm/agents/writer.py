import logging

import pydantic_ai

import app.swarm.content_pages.tools as content_pages_tools
import app.swarm.context.tools as context_tools
import app.swarm.models as models

logger = logging.getLogger(__name__)

writer_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
    toolsets=[
        content_pages_tools.content_pages_toolset,
        context_tools.context_documents_toolset,
    ],
)


@writer_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    deps = ctx.deps
    logger.info("[Tool Call] Writer agent: get_instructions called")

    return await deps.prompt_repository.get_prompt_by_name("writer.md")


@writer_agent.tool
async def create_page(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
    page_key: str,
    content: str,
) -> str:
    """Create a new markdown content page in the run's content page store.

    The main content page should use the key 'main'. The writer may also create
    sub-pages using keys like 'sub/<slug>' for auxiliary content based on its
    own reasoning or critic feedback.

    Args:
        page_key: The key for the page (e.g. 'main', 'sub/related-content').
        content: The full markdown content of the page.

    Returns a confirmation, or an error if the page key is already taken.
    """
    logger.info("[Tool Call] Writer agent: create_page called")

    if page_key in ctx.deps.content_pages:
        return f"Page '{page_key}' already exists. Use update_page to modify it."

    ctx.deps.content_pages[page_key] = content
    logger.info("Writer created page: %s", page_key)

    await ctx.deps.content_pages_repository.save_page(
        ctx.deps.run_config.run_id, page_key, content
    )

    return f"Page '{page_key}' created."


@writer_agent.tool
async def update_page(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
    page_key: str,
    content: str,
) -> str:
    """Replace the full content of an existing markdown content page.

    Read the page first, make your changes, then write the complete updated
    content back. The previous version is fully replaced.

    Args:
        page_key: The key of the page to update.
        content: The complete new markdown content.

    Returns a confirmation, or an error if the page does not exist.
    """
    logger.info("[Tool Call] Writer agent: update_page called")

    if page_key not in ctx.deps.content_pages:
        return f"Page '{page_key}' not found. Existing pages: {list(ctx.deps.content_pages.keys())}"

    ctx.deps.content_pages[page_key] = content
    logger.info("Writer updated page: %s", page_key)

    await ctx.deps.content_pages_repository.save_page(
        ctx.deps.run_config.run_id, page_key, content
    )

    return f"Page '{page_key}' updated."
