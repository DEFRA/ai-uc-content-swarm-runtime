import pytest
from pydantic_ai.models import function as function_models

from app.swarm import models


class TestAgentModelMapping:
    def test_get_model_mapping_by_name(self) -> None:
        mapping = models.ModelMapping()
        model_a = function_models.FunctionModel(
            model_name="first_model",
            function=lambda x: x,
        )
        mapping.append("researcher", model_a)

        result = mapping.get("researcher")
        assert result is model_a

    def test_get_nonexistent_mapping_raises_key_error(self) -> None:
        mapping = models.ModelMapping()

        with pytest.raises(KeyError, match="No LLM model mapping for agent"):
            mapping.get("does_not_exist")

    def test_adding_model_mapping(self) -> None:
        mapping = models.ModelMapping()
        model_a = function_models.FunctionModel(
            model_name="first_model",
            function=lambda x: x,
        )
        mapping.append("agent_a", model_a)

        assert mapping.get("agent_a") is model_a

    def test_adding_colliding_mapping_overwrites(self) -> None:
        mapping = models.ModelMapping()

        first = function_models.FunctionModel(
            model_name="first_model",
            function=lambda x: x,
        )
        second = function_models.FunctionModel(
            model_name="second_model",
            function=lambda x: x,
        )

        mapping.append("agent_x", first)

        with pytest.raises(
            ValueError, match="Agent 'agent_x' already has a model mapping"
        ):
            mapping.append("agent_x", second)

        assert mapping.get("agent_x") is first


def test_agent_name_researcher_value() -> None:
    assert models.AgentName.RESEARCHER == "researcher"


def test_agent_name_writer_value() -> None:
    assert models.AgentName.WRITER == "writer"


def test_agent_name_is_str() -> None:
    assert isinstance(models.AgentName.RESEARCHER, str)
    assert isinstance(models.AgentName.WRITER, str)


def test_agent_name_used_as_dict_key() -> None:
    d: dict[models.AgentName, str] = {
        models.AgentName.RESEARCHER: "research agent",
    }
    assert d[models.AgentName.RESEARCHER] == "research agent"


def test_group_chat_empty_transcript() -> None:
    gc = models.GroupChat()
    assert gc.format_transcript() == ""


def test_group_chat_format_transcript_contains_exchange() -> None:
    gc = models.GroupChat()
    gc.transcript.append(
        models.AgentExchange(
            agent_name="researcher",
            message="What does the policy say?",
            response="The policy requires X.",
        )
    )
    result = gc.format_transcript()
    assert "## Recent discussion:" in result
    assert "**researcher**: The policy requires X." in result


def test_group_chat_agents_defaults_to_empty() -> None:
    gc = models.GroupChat()
    assert gc.agents == {}


def test_group_chat_agent_name_lookup() -> None:
    gc = models.GroupChat(agents={models.AgentName.RESEARCHER: object()})
    assert models.AgentName.RESEARCHER in gc.agents


def test_group_chat_absent_agent_not_in_agents() -> None:
    gc = models.GroupChat(agents={models.AgentName.RESEARCHER: object()})
    assert models.AgentName.WRITER not in gc.agents
