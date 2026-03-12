"""Models for the swarm module."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

import pydantic_ai.models

from app.swarm.context import models as context_models
from app.swarm.context import repository as context_repo
from app.swarm.prompts import repository as prompt_repo


@dataclass
class AgentExchange:
    agent_name: str
    message: str
    response: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class RunConfig:
    """Configuration for a swarm run."""

    task: str
    id: str
    name: str
    context_documents: list[context_models.ContextDocument] = field(
        default_factory=list
    )


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
        except KeyError as err:
            msg = f"No LLM model mapping for agent '{agent_name}'"
            raise KeyError(msg) from err

    def as_dict(self) -> dict[str, pydantic_ai.models.Model]:
        return dict(self._backing)


@dataclass
class AgentDependencies:
    run_config: RunConfig
    context_repository: context_repo.AbstractContextRepository
    group_chat: list[AgentExchange] = field(default_factory=list)
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
            lines.append(f"\n**{exchange.agent_name}**:")
            lines.append(f"Q: {exchange.message}")
            lines.append(f"A: {exchange.response}")
        return "\n".join(lines)

    def get_model_for_agent(self, agent_name: str) -> pydantic_ai.models.Model:
        """Return the LLM model mapped to `agent_name`.

        Raises: KeyError if no mapping exists.
        """
        return self.llm_mapping.get(agent_name)
