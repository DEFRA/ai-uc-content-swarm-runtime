import json
import logging

import pydantic_ai

import app.swarm.models as models

logger = logging.getLogger(__name__)

content_pages_toolset: pydantic_ai.FunctionToolset[models.AgentDependencies] = (
    pydantic_ai.FunctionToolset()
)


@content_pages_toolset.tool
async def list_pages(ctx: pydantic_ai.RunContext[models.AgentDependencies]) -> str:
    """List the keys of all content pages available for review."""
    logger.info("[Tool Call] ContentPagesToolset: list_pages called")
    if not ctx.deps.content_pages:
        return "No content pages have been created yet."
    return json.dumps(list(ctx.deps.content_pages.keys()), indent=2)


@content_pages_toolset.tool
async def read_page(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], page_key: str
) -> str:
    """Read the current content of a content page for review.

    Args:
        page_key: The key of the page to read (e.g. 'main', 'sub/related').
    """
    logger.info("[Tool Call] ContentPagesToolset: read_page called")
    if page_key not in ctx.deps.content_pages:
        return f"Page '{page_key}' not found. Existing pages: {list(ctx.deps.content_pages.keys())}"
    return ctx.deps.content_pages[page_key]
