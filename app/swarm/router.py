from typing import Annotated

import fastapi

import app.swarm.dependencies as dependencies
import app.swarm.runner as runner
from app.swarm.api_schemas import RunRequest, RunResponse

router = fastapi.APIRouter(prefix="/swarm", tags=["swarm"])


@router.post("/run")
async def run_swarm(
    request: RunRequest,
    runner: Annotated[
        runner.SwarmRunner, fastapi.Depends(dependencies.get_swarm_runner)
    ],
) -> RunResponse:
    output = await runner.start_run(request.task)

    return RunResponse(output=output)
