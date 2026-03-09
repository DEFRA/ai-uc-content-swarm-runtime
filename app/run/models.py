import uuid
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
    _contexts: list[ContextMetadata] = field(default_factory=list)
    _context_map: dict[uuid.UUID, ContextMetadata] = field(
        default_factory=dict, init=False
    )

    def add_context(self, context: ContextMetadata) -> None:
        self._context_map[context.id] = context

        self._contexts = list(self._context_map.values())

    @property
    def contexts(self) -> list[ContextMetadata]:
        return self._contexts

    def get_context(self, context_id: uuid.UUID) -> ContextMetadata | None:
        return self._context_map.get(context_id)
    
    def __post_init__(self) -> None:
        """Initialize _context_map from _contexts after dataclass init."""
        for context in self._contexts:
            self._context_map[context.id] = context


class RunNotFoundError(Exception):
    """Exception raised when a run is not found"""
