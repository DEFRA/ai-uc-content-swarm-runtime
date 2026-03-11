from dataclasses import dataclass, field
from enum import StrEnum

import pydantic_ai.models

from app.swarm.prompts import repository as prompt_repo


class ContextType(StrEnum):
    POLICY = "policy"
    LEGLISLATION = "legislation"


@dataclass
class ContextDocument:
    type: ContextType
    name: str
    content: str


@dataclass
class AgentExchange:
    """A single turn in the group discussion."""

    agent_name: str
    agent_role: str
    question: str
    response: str
    turn_number: int = field(default=0)


@dataclass
class ModelMapping:
    """Simple dataclass wrapper around a backing dict for agent->model mapping."""

    _backing: dict[str, pydantic_ai.models.Model] = field(default_factory=dict)

    def append(self, agent_name: str, model: pydantic_ai.models.Model) -> None:
        if agent_name in self._backing:
            msg = f"Agent '{agent_name}' already has a model mapping"
            raise ValueError(msg)

        self._backing[agent_name] = model

    def get(self, agent_name: str) -> pydantic_ai.models.Model:
        try:
            return self._backing[agent_name]
        except KeyError as exc:
            msg = f"No LLM model mapping for agent '{agent_name}'"
            raise KeyError(msg) from exc

    def as_dict(self) -> dict[str, pydantic_ai.models.Model]:
        return dict(self._backing)


@dataclass
class AgentDependencies:
    group_chat: list[AgentExchange] = field(default_factory=list)
    context_documents: list[ContextDocument] = field(default_factory=list)
    prompt_repository: prompt_repo.AbstractPromptRepository = field(
        default_factory=prompt_repo.FileSystemPromptRepository
    )
    llm_mapping: ModelMapping = field(default_factory=ModelMapping)

    def format_chat_context(self) -> str:
        """Format the discussion as readable context for agents."""
        if not self.group_chat:
            return ""
        lines = ["## Recent discussion:"]
        for exchange in self.group_chat:
            lines.append(f"\n**{exchange.agent_name}** ({exchange.agent_role}):")
            lines.append(f"Q: {exchange.question}")
            lines.append(f"A: {exchange.response}")
        return "\n".join(lines)

    def get_model_for_agent(self, agent_name: str) -> pydantic_ai.models.Model:
        """Return the LLM model mapped to `agent_name`.

        Raises KeyError if there is no mapping for the given agent.
        """
        return self.llm_mapping.get(agent_name)
