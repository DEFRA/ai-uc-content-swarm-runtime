import logging

import pydantic_ai

import app.swarm.models as models

logger = logging.getLogger(__name__)

_STYLE_GUIDE_IDX = "content-style-guide/index.json"
_CONTENT_GUIDANCE_IDX = "content-guidance/index.json"

context_documents_toolset: pydantic_ai.FunctionToolset[models.AgentDependencies] = (
    pydantic_ai.FunctionToolset()
)


@context_documents_toolset.tool
async def list_style_guide_documents(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content style guide rules available in the context store.

    Returns a JSON array of objects with title, description, and file fields.
    Use the file value with get_document_content to retrieve the full content of the rule.
    """
    logger.info(
        "[Tool Call] ContextDocumentsToolset: list_style_guide_documents called"
    )
    return await ctx.deps.context_repository.get_context(_STYLE_GUIDE_IDX)


@context_documents_toolset.tool
async def list_content_guidance(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the GOV.UK content guidance documents available in the context store.

    Returns a JSON array of objects with id, title, description, and file fields.
    The file field is the path to use with get_document_content to retrieve the full content of the guidance.
    """
    logger.info("[Tool Call] ContextDocumentsToolset: list_content_guidance called")
    return await ctx.deps.context_repository.get_context(_CONTENT_GUIDANCE_IDX)


@context_documents_toolset.tool
async def get_document_content(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], file: str
) -> str:
    """Retrieve the full content of a GOV.UK context document by its file path.

    Use the file path returned by list_style_guide_documents or list_content_guidance.
    """
    logger.info("[Tool Call] ContextDocumentsToolset: get_document_content called")
    try:
        return await ctx.deps.context_repository.get_context(file)
    except Exception as e:
        return f"Error retrieving document content for file '{file}': {str(e)}"
