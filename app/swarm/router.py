from typing import Annotated

import pydantic
from fastapi import APIRouter, Depends

import app.swarm.dependencies as dependencies
import app.swarm.runner as runner

router = APIRouter(prefix="/swarm", tags=["swarm"])


class RunRequest(pydantic.BaseModel):
    task: str


class RunResponse(pydantic.BaseModel):
    output: str


@router.post("/run")
async def run_swarm(
    request: RunRequest,
    runner: Annotated[runner.SwarmRunner, Depends(dependencies.get_swarm_runner)],
) -> RunResponse:
    output = await runner.run(request.task)
    return RunResponse(output=output)
