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
