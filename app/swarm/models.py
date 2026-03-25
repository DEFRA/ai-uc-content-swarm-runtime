"""Models for the swarm module."""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

import pydantic_ai
import pydantic_ai.messages
import pydantic_ai.models

from app.swarm.content_pages import repository as content_pages_repo
from app.swarm.context import models as context_models
from app.swarm.context import repository as context_repo
from app.swarm.prompts import repository as prompt_repo


class AgentName(StrEnum):
    MANAGER = "manager"
    RESEARCHER = "researcher"
    WRITER = "writer"
    CRITIC = "critic"


@dataclass
class SwarmJob:
    run_id: str
    task: str
    name: str
    context_documents: list[context_models.ContextDocument]

    @classmethod
    def from_message_body(cls, body: str) -> "SwarmJob":
        """Deserialize a job from an SQS message body.

        Args:
            body: The JSON message body from SQS.

        Returns:
            A SwarmJob instance with parsed context documents.
        """
        data = json.loads(body)

        context_documents = [
            context_models.ContextDocument(
                id=UUID(doc["id"]),
                type=context_models.ContextType.POLICY,
                name=doc["name"],
                description=doc.get("description"),
                path=doc["path"],
            )
            for doc in data.get("context_documents", [])
        ]

        return cls(
            run_id=data["run_id"],
            task=data["task"],
            name=data["name"],
            context_documents=context_documents,
        )


@dataclass
class AgentExchange:
    agent_name: str
    message: str
    response: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GroupChat:
    """Holds the active agents and the growing conversation transcript."""

    agents: dict[AgentName, "pydantic_ai.Agent[AgentDependencies, str]"] = field(
        default_factory=dict
    )
    transcript: list[AgentExchange] = field(default_factory=list)

    def format_transcript(self) -> str:
        """Format the transcript as readable context for agents."""
        if not self.transcript:
            return ""
        lines = ["## Recent discussion:"]
        for exchange in self.transcript:
            lines.append(f"\n**{exchange.agent_name}**: {exchange.response}")
        return "\n".join(lines)


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
    run_config: SwarmJob
    context_repository: context_repo.AbstractContextRepository
    content_pages_repository: content_pages_repo.AbstractContentPagesRepository
    group_chat: GroupChat = field(default_factory=GroupChat)
    prompt_repository: prompt_repo.AbstractPromptRepository = field(
        default_factory=prompt_repo.FileSystemPromptRepository
    )
    llm_mapping: ModelMapping = field(default_factory=ModelMapping)
    content_pages: dict[str, str] = field(default_factory=dict)
    context_history: dict[str, list[pydantic_ai.messages.ModelMessage]] = field(
        default_factory=dict
    )

    def get_model_for_agent(self, agent_name: str) -> pydantic_ai.models.Model:
        """Return the LLM model mapped to `agent_name`.

        Raises: KeyError if no mapping exists.
        """
        return self.llm_mapping.get(agent_name)
