import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.swarm import models


@pytest.fixture
def agent_deps(mocker) -> models.AgentDependencies:
    return models.AgentDependencies(
        run_config=models.RunConfig(task="test task", id="run-1", name="test"),
        context_repository=mocker.MagicMock(),
        content_pages_repository=mocker.MagicMock(),
    )


def test_context_history_empty_by_default(
    agent_deps: models.AgentDependencies,
) -> None:
    assert agent_deps.context_history == {}


def test_context_history_stores_pydantic_ai_messages(
    agent_deps: models.AgentDependencies,
) -> None:
    messages = [
        ModelRequest(parts=[UserPromptPart(content="research this")]),
        ModelResponse(parts=[TextPart(content="here are findings")], model_name="test"),
    ]
    agent_deps.context_history["researcher"] = messages

    assert len(agent_deps.context_history["researcher"]) == 2
    assert isinstance(agent_deps.context_history["researcher"][0], ModelRequest)
    assert isinstance(agent_deps.context_history["researcher"][1], ModelResponse)


def test_context_history_isolated_per_agent(
    agent_deps: models.AgentDependencies,
) -> None:
    agent_deps.context_history["researcher"] = [
        ModelRequest(parts=[UserPromptPart(content="research prompt")]),
    ]
    agent_deps.context_history["writer"] = [
        ModelRequest(parts=[UserPromptPart(content="write prompt")]),
    ]

    assert len(agent_deps.context_history["researcher"]) == 1
    assert len(agent_deps.context_history["writer"]) == 1
    assert agent_deps.context_history.get("manager") is None


def test_context_history_accumulates_across_dispatches(
    agent_deps: models.AgentDependencies,
) -> None:
    # Simulate what dispatch does: all_messages() returns previous + new, so
    # assigning it each time naturally grows the history.
    first_run = [
        ModelRequest(parts=[UserPromptPart(content="first task")]),
        ModelResponse(parts=[TextPart(content="first response")], model_name="test"),
    ]
    agent_deps.context_history["researcher"] = first_run

    second_run = first_run + [
        ModelRequest(parts=[UserPromptPart(content="second task")]),
        ModelResponse(parts=[TextPart(content="second response")], model_name="test"),
    ]
    agent_deps.context_history["researcher"] = second_run

    assert len(agent_deps.context_history["researcher"]) == 4


def test_context_history_independent_for_each_agent(
    agent_deps: models.AgentDependencies,
) -> None:
    agent_deps.context_history["researcher"] = [
        ModelRequest(parts=[UserPromptPart(content="researcher task")]),
        ModelResponse(parts=[TextPart(content="researcher answer")], model_name="test"),
    ]
    agent_deps.context_history["writer"] = [
        ModelRequest(parts=[UserPromptPart(content="writer task")]),
        ModelResponse(parts=[TextPart(content="writer answer")], model_name="test"),
        ModelRequest(parts=[UserPromptPart(content="writer follow-up")]),
    ]

    assert len(agent_deps.context_history["researcher"]) == 2
    assert len(agent_deps.context_history["writer"]) == 3
