from dataclasses import dataclass, field
from enum import StrEnum

import pydantic_ai.messages


class ContextType(StrEnum):
    POLICY = "policy"
    LEGLISLATION = "legislation"


@dataclass
class ContextDocument:
    type: ContextType
    name: str
    content: str


@dataclass
class AgentDependencies:
    group_chat: list[pydantic_ai.messages.ModelMessage] = field(default_factory=list)
    context_documents: list[ContextDocument] = field(default_factory=list)
