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
    _context_map: dict[uuid.UUID, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        """Populate the internal context map from the provided contexts.

        This ensures `get_context` works for Run instances constructed with
        an initial `_contexts` list (e.g. in tests or deserialization).
        """
        for idx, ctx in enumerate(self._contexts):
            self._context_map[ctx.id] = idx

    def add_context(self, context: ContextMetadata) -> None:
        self._context_map[context.id] = len(self._contexts)

        self._contexts.append(context)

    @property
    def contexts(self) -> tuple[ContextMetadata, ...]:
        """Return contexts as an immutable tuple to prevent external mutation."""
        return tuple(self._contexts)

    def get_context(self, context_id: uuid.UUID) -> ContextMetadata | None:
        idx = self._context_map.get(context_id)

        if idx is not None:
            return self._contexts[idx]

        return None


class RunNotFoundError(Exception):
    """Exception raised when a run is not found"""
