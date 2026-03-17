import json
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

    return await deps.prompt_repository.get_prompt_by_name("writer.md")


@writer_agent.tool
async def list_content_guidance(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content guidance documents available in the context store.

    Returns a JSON array of objects with id, title, and description fields.
    Use the id value with get_document_content to retrieve the full document.
    """
    raw = await ctx.deps.context_repository.get_context(content_guidance_idx)
    entries = json.loads(raw)

    docs = [
        {
            "id": e["id"],
            "title": e["title"],
            "description": e.get("description", ""),
        }
        for e in entries
    ]

    return json.dumps(docs, indent=2)


@writer_agent.tool
async def list_style_guide_documents(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content style guide rules available in the context store.

    Returns a JSON array of objects with id, title, and description fields.
    Use the id value with get_document_content to retrieve the full document.
    """
    raw = await ctx.deps.context_repository.get_context(style_guide_idx)
    entries = json.loads(raw)

    docs = [
        {
            "id": e["id"],
            "title": e["title"],
            "description": e.get("description", ""),
        }
        for e in entries
    ]

    return json.dumps(docs, indent=2)


@writer_agent.tool
async def get_document_content(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], doc_id: str
) -> str:
    """Retrieve the full content of a GOV.UK context document by its id.

    Use the id returned by list_content_guidance or list_style_guide_documents.
    """
    indexes = [
        (content_guidance_idx, "content-guidance"),
        (style_guide_idx, "content-style-guide"),
    ]

    for index_path, prefix in indexes:
        raw = await ctx.deps.context_repository.get_context(index_path)
        entries = json.loads(raw)
        for entry in entries:
            if entry["id"] == doc_id:
                path = f"{prefix}/{entry['file']}"
                logger.info("Writer fetching document id=%s path=%s", doc_id, path)
                return await ctx.deps.context_repository.get_context(path)

    return f"Document with id '{doc_id}' not found."


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
    return content_page_tools.read_page(ctx.deps, page_key)


@writer_agent.tool
async def list_pages(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the keys of all content pages created so far in this run."""
    return content_page_tools.list_pages(ctx.deps)
