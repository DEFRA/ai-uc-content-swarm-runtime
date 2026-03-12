"""Models for context documents."""

import uuid
from dataclasses import dataclass
from enum import StrEnum


class ContextType(StrEnum):
    """Type classification for context documents."""

    POLICY = "policy"
    LEGISLATION = "legislation"
    STYLE_GUIDE = "style_guide"


@dataclass
class ContextDocument:
    """A context document."""

    id: uuid.UUID
    type: ContextType
    name: str
    path: str
    description: str | None = None
