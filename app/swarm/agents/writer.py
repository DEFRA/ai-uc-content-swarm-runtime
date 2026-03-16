import json
import logging

import pydantic_ai

import app.swarm.models as models

logger = logging.getLogger(__name__)

_CONTENT_GUIDANCE_INDEX = "content-guidance/index.json"
_STYLE_GUIDE_INDEX = "content-style-guide/index.json"

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

    Returns a JSON array of objects with id, title, description, and path fields.
    Use the path value with get_document_content to retrieve the full document.
    """
    raw = await ctx.deps.context_repository.get_context(_CONTENT_GUIDANCE_INDEX)
    entries = json.loads(raw)

    docs = [
        {
            "id": e["id"],
            "title": e["title"],
            "description": e.get("description", ""),
            "path": f"content-guidance/{e['file']}",
        }
        for e in entries
    ]

    return json.dumps(docs, indent=2)


@writer_agent.tool
async def list_style_guide_documents(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content style guide rules available in the context store.

    Returns a JSON array of objects with id, title, description, and path fields.
    Use the path value with get_document_content to retrieve the full document.
    """
    raw = await ctx.deps.context_repository.get_context(_STYLE_GUIDE_INDEX)
    entries = json.loads(raw)

    docs = [
        {
            "id": e["id"],
            "title": e["title"],
            "description": e.get("description", ""),
            "path": f"content-style-guide/{e['file']}",
        }
        for e in entries
    ]

    return json.dumps(docs, indent=2)


@writer_agent.tool
async def get_document_content(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], path: str
) -> str:
    """Retrieve the full content of a GOV.UK context document by its path.

    Use the path returned by list_content_guidance or list_style_guide_documents.
    """
    logger.info("Writer fetching document: %s", path)

    return await ctx.deps.context_repository.get_context(path)
