import json
import logging
import uuid

import pydantic_ai

from app.swarm import models
from app.swarm.context import repository

logger = logging.getLogger(__name__)

researcher_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@researcher_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    logger.info("[Tool Call] Researcher agent: get_instructions called")
    deps = ctx.deps

    return await deps.prompt_repository.get_prompt_by_name("researcher.md")


@researcher_agent.tool
async def list_policy_documents(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the policy documents that the manager agent has shared for this run."""
    logger.info("[Tool Call] Researcher agent: list_policy_documents called")
    policy_docs = [
        doc
        for doc in ctx.deps.run_config.context_documents
        if doc.type == models.context_models.ContextType.POLICY
    ]

    if not policy_docs:
        return "No policy documents have been shared yet."

    doc_list = json.dumps(
        [{"id": str(doc.id), "name": doc.name} for doc in policy_docs],
        indent=2,
    )

    return f"The following policy documents are available:\n{doc_list}\n"


@researcher_agent.tool
async def get_document_content(
    ctx: pydantic_ai.RunContext[models.AgentDependencies], context_id: uuid.UUID
) -> str:
    """Retrieve the content of a context document by its key."""
    logger.info("[Tool Call] Researcher agent: get_document_content called")
    run_config = ctx.deps.run_config

    doc = next(
        (doc for doc in run_config.context_documents if doc.id == context_id), None
    )

    if not doc:
        return f"Document with id {context_id} not found in run configuration."

    try:
        return await ctx.deps.context_repository.get_context(doc.path)
    except repository.ContextNotFoundError:
        return f"Document with id {context_id} not found in context repository"
