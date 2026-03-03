from dataclasses import dataclass, field

import pydantic_ai.messages


@dataclass
class AgentDependencies:
    messages: list[pydantic_ai.messages.ModelMessage] = field(default_factory=list)
