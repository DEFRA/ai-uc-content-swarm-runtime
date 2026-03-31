import uuid
from datetime import UTC, datetime
from typing import Annotated

import fastapi

import app.run.api_schemas as api_schemas
import app.run.context.router as context_router
import app.run.dependencies as run_dependencies
import app.run.models as models
import app.run.service as run_service

router = fastapi.APIRouter(prefix="/runs", tags=["runs"])

router.include_router(context_router.router)


@router.post("/", status_code=fastapi.status.HTTP_201_CREATED)
async def create_run(
    request: api_schemas.RunCreateRequest,
    service: Annotated[
        run_service.RunService, fastapi.Depends(run_dependencies.get_run_service)
    ],
) -> api_schemas.RunResponse:
    """Create a new run.

    Args:
        request: The run creation request.
        service: The RunService instance (injected).

    Returns:
        The created Run record with status=pending.
    """
    now = datetime.now(tz=UTC)

    run = models.Run(
        id=str(uuid.uuid4()),
        name=request.name,
        status=models.RunStatus.SETUP,
        created_at=now,
        updated_at=now,
    )

    run = await service.setup_run(run)

    return api_schemas.RunResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        result=run.result,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.get("/{run_id}")
async def get_run(
    run_id: str,
    service: Annotated[
        run_service.RunService, fastapi.Depends(run_dependencies.get_run_service)
    ],
) -> api_schemas.RunResponse:
    """Retrieve a run by ID.

    Args:
        run_id: The ID of the run to retrieve.
        service: The RunService instance (injected).

    Returns:
        The Run record with all associated contexts.

    Raises:
        HTTPException: 404 if the run is not found.
    """
    run = await service.get_run(run_id)

    if not run:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Run with id {run_id} not found",
        )

    return api_schemas.RunResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        result=run.result,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


@router.post("/{run_id}/start", status_code=fastapi.status.HTTP_202_ACCEPTED)
async def start_run(
    run_id: str,
    service: Annotated[
        run_service.RunService, fastapi.Depends(run_dependencies.get_run_service)
    ],
) -> api_schemas.RunResponse:
    """Start a run by publishing a job to the SQS queue.

    Updates the run status to PENDING and publishes the job to the swarm queue.

    Args:
        run_id: The ID of the run to start.
        service: The RunService instance (injected).

    Returns:
        The updated Run record with status=PENDING.

    Raises:
        HTTPException: 404 if the run is not found.
    """
    try:
        run = await service.start_run(run_id)
    except models.RunNotFoundError:
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_404_NOT_FOUND,
            detail=f"Run with id {run_id} not found",
        ) from None

    return api_schemas.RunResponse(
        id=run.id,
        name=run.name,
        status=run.status,
        result=run.result,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )
