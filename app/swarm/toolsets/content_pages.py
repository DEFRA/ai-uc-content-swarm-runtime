import logging

import pydantic_ai
from pydantic_ai import FunctionToolset

import app.swarm.content_pages.tools as content_page_tools
import app.swarm.models as models

logger = logging.getLogger(__name__)

content_pages_toolset: FunctionToolset[models.AgentDependencies] = FunctionToolset()


@content_pages_toolset.tool
async def list_pages(ctx: pydantic_ai.RunContext[models.AgentDependencies]) -> str:
    """List the keys of all content pages available for review."""
    logger.info("[Tool Call] ContentPagesToolset: list_pages called")
    return content_page_tools.list_pages(ctx.deps)


@content_pages_toolset.tool
async def read_page(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], page_key: str
) -> str:
    """Read the current content of a content page for review.

    Args:
        page_key: The key of the page to read (e.g. 'main', 'sub/related').
    """
    logger.info("[Tool Call] ContentPagesToolset: read_page called")
    return content_page_tools.read_page(ctx.deps, page_key)
