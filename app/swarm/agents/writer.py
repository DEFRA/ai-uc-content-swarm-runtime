import logging

import pydantic_ai

import app.swarm.content_pages.tools as content_page_tools
import app.swarm.models as models

logger = logging.getLogger(__name__)

content_guidance_idx = "content-guidance/index.json"
style_guide_idx = "content-style-guide/index.json"

writer_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@writer_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    deps = ctx.deps
    logger.info("[Tool Call] Writer agent: get_instructions called")

    return await deps.prompt_repository.get_prompt_by_name("writer.md")


@writer_agent.tool
async def list_content_guidance(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content guidance documents available in the context store.

    Returns a JSON array of objects with id, title, description, and file fields.
    The file field is the path to use with get_document_content to retrieve the full content of the guidance.
    Use the id value with get_document_content to retrieve the full document.
    """
    logger.info("[Tool Call] Writer agent: list_content_guidance called")
    return await ctx.deps.context_repository.get_context(content_guidance_idx)


@writer_agent.tool
async def list_style_guide_documents(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content style guide rules available in the context store.

    Returns a JSON array of objects with title, description, and file fields.
    The file field is the path to use with get_document_content to retrieve the full content of the rule.
    Use the id value with get_document_content to retrieve the full document.
    """
    logger.info("[Tool Call] Writer agent: list_style_guide_documents called")

    return await ctx.deps.context_repository.get_context(style_guide_idx)


@writer_agent.tool
async def get_document_content(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], file: str
) -> str:
    """Retrieve the full content of a GOV.UK context document by its id.

    Use the id returned by list_content_guidance or list_style_guide_documents.
    """
    logger.info("[Tool Call] Writer agent: get_document_content called")

    try:
        return await ctx.deps.context_repository.get_context(file)
    except Exception as e:
        return f"Error retrieving document content for file '{file}': {str(e)}"


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
        ctx.deps.run_config.id, page_key, content
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
        ctx.deps.run_config.id, page_key, content
    )

    return f"Page '{page_key}' updated."


@writer_agent.tool
async def read_page(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], page_key: str
) -> str:
    """Read the current content of an existing content page."""
    logger.info("[Tool Call] Writer agent: read_page called")
    return content_page_tools.read_page(ctx.deps, page_key)


@writer_agent.tool
async def list_pages(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the keys of all content pages created so far in this run."""
    logger.info("[Tool Call] Writer agent: list_pages called")
    return content_page_tools.list_pages(ctx.deps)
