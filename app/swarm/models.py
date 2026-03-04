from dataclasses import dataclass, field
from enum import Enum

import pydantic_ai.messages


class ContextTypeEnum(Enum):
    POLICY = "policy"
    LEGLISLATION = "legislation"


@dataclass
class ContextDocument:
    type: ContextTypeEnum
    name: str
    content: str


@dataclass
class AgentDependencies:
    group_chat: list[pydantic_ai.messages.ModelMessage] = field(default_factory=list)
    context_documents: list[ContextDocument] = field(default_factory=list)
