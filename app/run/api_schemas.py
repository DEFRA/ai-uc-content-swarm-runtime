from datetime import datetime

import pydantic

from app.run.models import RunStatus


class RunCreateRequest(pydantic.BaseModel):
    """Request model for creating a new run."""

    name: str = pydantic.Field(..., description="Name of the run")
    task: str | None = pydantic.Field(
        default=None, description="Optional task description for the swarm"
    )


class RunStartRequest(pydantic.BaseModel):
    """Request model for starting a run."""

    task: str | None = pydantic.Field(
        default=None, description="Optional task to override the run's task"
    )


class RunResponse(pydantic.BaseModel):
    """Response model for a run."""

    id: str = pydantic.Field(..., description="Unique identifier for the run")

    name: str = pydantic.Field(..., description="Human-readable name of the run")

    status: RunStatus = pydantic.Field(..., description="Current status of the run")

    task: str | None = pydantic.Field(
        default=None, description="Task description for the swarm"
    )

    result: str | None = pydantic.Field(
        default=None, description="Swarm execution result output"
    )

    created_at: datetime = pydantic.Field(..., description="When the run was created")

    updated_at: datetime = pydantic.Field(
        ..., description="When the run was last updated"
    )
