import json
import logging
import uuid

import pydantic_ai

import app.swarm.models as models

logger = logging.getLogger(__name__)

researcher_agent = pydantic_ai.Agent(
    deps_type=models.AgentDependencies,
    output_type=str,
)


@researcher_agent.instructions
async def get_instructions(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    deps = ctx.deps

    return await deps.prompt_repository.get_prompt_by_name("researcher.md")


@researcher_agent.tool
async def list_policy_documents(
    ctx: pydantic_ai.RunContext[models.AgentDependencies],
) -> str:
    """List the policy documents that the manager agent has shared for this run."""
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
    run_config = ctx.deps.run_config

    logger.info("Getting content for document with id: %s", context_id)

    doc = next(
        (doc for doc in run_config.context_documents if doc.id == context_id), None
    )

    if not doc:
        msg = f"Document with id {context_id} not found in context documents"
        raise ValueError(msg)

    return await ctx.deps.context_repository.get_context(doc.path)
