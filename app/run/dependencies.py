from typing import Annotated

import fastapi
from pymongo.asynchronous.database import AsyncDatabase

import app.common.mongo as mongo
import app.run.repository as repository
import app.run.service as run_service
import app.swarm.dependencies as swarm_dependencies
import app.swarm.runner as swarm_runner


def get_run_repository(
    db: AsyncDatabase = fastapi.Depends(mongo.get_db),
) -> repository.RunRepository:
    """Provide a RunRepository instance.

    Args:
        db: The AsyncDatabase instance (injected).

    Returns:
        A RunRepository instance backed by MongoDB.
    """
    return repository.MongoRunRepository(db)


def get_run_service(
    run_repository: Annotated[
        repository.RunRepository, fastapi.Depends(get_run_repository)
    ],
    swarm: Annotated[
        swarm_runner.SwarmRunner, fastapi.Depends(swarm_dependencies.get_swarm_runner)
    ],
) -> run_service.RunService:
    """Provide a RunService instance.

    Args:
        run_repository: The RunRepository instance (injected).
        swarm: The SwarmRunner instance (injected).

    Returns:
        A RunService instance.
    """
    return run_service.RunService(run_repository, swarm)
