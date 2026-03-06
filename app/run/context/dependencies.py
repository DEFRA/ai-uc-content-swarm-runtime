from typing import Annotated

import fastapi

from app.run import dependencies as run_dependencies
from app.run import repository
from app.run.context.service import ContextService


def get_context_service(
    run_repo: Annotated[
        repository.RunRepository, fastapi.Depends(run_dependencies.get_run_repository)
    ],
) -> ContextService:
    return ContextService(run_repo)
