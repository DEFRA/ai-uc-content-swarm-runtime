from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.run.context.models import ContextMetadata


class RunStatus(StrEnum):
    """Status of a run."""

    SETUP = "setup"
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class Run:
    """Complete run record with all lifecycle information."""

    id: str
    name: str
    status: RunStatus = RunStatus.SETUP
    created_at: datetime = datetime.now(tz=UTC)
    updated_at: datetime = datetime.now(tz=UTC)
    contexts: list[ContextMetadata] = field(default_factory=list)


class RunNotFoundError(Exception):
    """Exception raised when a run is not found"""
