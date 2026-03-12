from typing import Annotated

import fastapi

from app.swarm import api_schemas, dependencies, models, runner
from app.swarm.context import models as context_models

router = fastapi.APIRouter(prefix="/swarm", tags=["swarm"])


@router.post("/run")
async def run_swarm(
    request: api_schemas.RunRequest,
    runner: Annotated[
        runner.SwarmRunner, fastapi.Depends(dependencies.get_swarm_runner)
    ],
) -> api_schemas.RunResponse:
    config = models.RunConfig(
        task=request.task,
        id=request.id,
        name=request.name,
        context_documents=[
            context_models.ContextDocument(
                id=doc.id,
                type=context_models.ContextType.POLICY,
                name=doc.name,
                description=doc.description,
                path=doc.path,
            )
            for doc in request.context_documents
        ],
    )

    output = await runner.start_run(config)

    return api_schemas.RunResponse(output=output)
