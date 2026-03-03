from typing import Annotated

import pydantic
from fastapi import APIRouter, Depends

from app.swarm.dependencies import get_swarm_runner
from app.swarm.runner import SwarmRunner

router = APIRouter(prefix="/swarm", tags=["swarm"])


class RunRequest(pydantic.BaseModel):
    task: str


class RunResponse(pydantic.BaseModel):
    output: str


@router.post("/run")
async def run_swarm(
    request: RunRequest, runner: Annotated[SwarmRunner, Depends(get_swarm_runner)]
) -> RunResponse:
    output = await runner.run(request.task)
    return RunResponse(output=output)
