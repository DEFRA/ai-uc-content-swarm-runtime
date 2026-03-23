"""Tests for Bedrock LLM model setup."""

from unittest.mock import MagicMock

import pytest

from app import config
from app.swarm import llm


@pytest.fixture
def mock_bedrock_provider(mocker):
    """Mock the BedrockProvider to avoid AWS calls."""
    provider_class = mocker.patch("app.swarm.llm.bedrock_providers.BedrockProvider")
    mock_provider = MagicMock()
    mock_provider.model_profile.return_value = "mocked_profile"
    provider_class.return_value = mock_provider
    return mock_provider


@pytest.fixture
def mock_bedrock_models(mocker):
    """Mock BedrockConverseModel and BedrockModelSettings."""
    settings_class = mocker.patch("app.swarm.llm.bedrock_models.BedrockModelSettings")
    model_class = mocker.patch("app.swarm.llm.bedrock_models.BedrockConverseModel")
    mock_settings_instance = MagicMock()
    settings_class.return_value = mock_settings_instance
    mock_model_instance = MagicMock()
    model_class.return_value = mock_model_instance
    return settings_class, model_class, mock_settings_instance, mock_model_instance


def test_setup_model_with_inference_profile_and_guardrails(mock_bedrock_models):
    """Test _setup_model with inference profile and guardrails."""
    settings_class, model_class, mock_settings_instance, mock_model_instance = (
        mock_bedrock_models
    )

    # Mock config
    model_config = config.BedrockModelConfig(
        model_id="us.anthropic.claude-opus-4-5-20251101-v1:0",
        inference_profile="arn:aws:bedrock:us-east-2:123456789012:application-inference-profile/my-profile",
        guardrails=config.BedrockGuardrailConfig(id="gr-123", version="1"),
    )

    result = llm._setup_model(model_config)

    # Verify BedrockModelSettings was called with both guardrail and inference profile config
    settings_class.assert_called_once()
    call_kwargs = settings_class.call_args[1]
    assert "bedrock_guardrail_config" in call_kwargs
    assert call_kwargs["bedrock_guardrail_config"] == {
        "guardrailIdentifier": "gr-123",
        "guardrailVersion": "1",
        "trace": "enabled",
    }
    assert "bedrock_inference_profile" in call_kwargs
    assert (
        call_kwargs["bedrock_inference_profile"]
        == "arn:aws:bedrock:us-east-2:123456789012:application-inference-profile/my-profile"
    )

    # Verify BedrockConverseModel was called with model_id as model_name
    model_class.assert_called_once()
    call_args = model_class.call_args
    assert call_args[0][0] == "us.anthropic.claude-opus-4-5-20251101-v1:0"
    assert call_args[1]["settings"] == mock_settings_instance

    assert result == mock_model_instance


def test_setup_model_with_inference_profile_only(mock_bedrock_models):
    """Test _setup_model with inference profile and no guardrails."""
    settings_class, model_class, mock_settings_instance, mock_model_instance = (
        mock_bedrock_models
    )

    model_config = config.BedrockModelConfig(
        model_id="anthropic.claude-sonnet-4-5-20250929-v1:0",
        inference_profile="my-profile",
        guardrails=None,
    )

    result = llm._setup_model(model_config)

    # Verify BedrockModelSettings was called with inference profile only
    settings_class.assert_called_once()
    call_kwargs = settings_class.call_args[1]
    assert "bedrock_inference_profile" in call_kwargs
    assert call_kwargs["bedrock_inference_profile"] == "my-profile"
    assert "bedrock_guardrail_config" not in call_kwargs

    # Verify BedrockConverseModel was called with settings
    model_class.assert_called_once()
    call_args = model_class.call_args
    assert call_args[0][0] == "anthropic.claude-sonnet-4-5-20250929-v1:0"
    assert call_args[1]["settings"] == mock_settings_instance

    assert result == mock_model_instance


def test_setup_model_with_inference_profile_and_guardrails_draft(mock_bedrock_models):
    """Test _setup_model with inference profile and DRAFT guardrail version."""
    settings_class, model_class, mock_settings_instance, mock_model_instance = (
        mock_bedrock_models
    )

    model_config = config.BedrockModelConfig(
        model_id="anthropic.claude-sonnet-4-5-20250929-v1:0",
        inference_profile="my-profile",
        guardrails=config.BedrockGuardrailConfig(id="gr-456", version="DRAFT"),
    )

    result = llm._setup_model(model_config)

    # Verify BedrockModelSettings was called with both configs
    settings_class.assert_called_once()
    call_kwargs = settings_class.call_args[1]
    assert "bedrock_guardrail_config" in call_kwargs
    assert call_kwargs["bedrock_guardrail_config"] == {
        "guardrailIdentifier": "gr-456",
        "guardrailVersion": "DRAFT",
        "trace": "enabled",
    }
    assert "bedrock_inference_profile" in call_kwargs
    assert call_kwargs["bedrock_inference_profile"] == "my-profile"

    model_class.assert_called_once()
    call_args = model_class.call_args
    assert call_args[1]["settings"] == mock_settings_instance

    assert result == mock_model_instance


def test_setup_model_uses_model_id_as_model_name(mock_bedrock_models):
    """Test that _setup_model uses model_id as the model name."""
    settings_class, model_class, mock_settings_instance, mock_model_instance = (
        mock_bedrock_models
    )

    model_config = config.BedrockModelConfig(
        model_id="my-custom-model:0",
        inference_profile="arn:aws:bedrock:us-east-1:123456789012:application-inference-profile/custom",
        guardrails=None,
    )

    result = llm._setup_model(model_config)

    # Verify the model name passed to BedrockConverseModel is the model_id
    model_class.assert_called_once()
    call_args = model_class.call_args
    assert call_args[0][0] == "my-custom-model:0"

    assert result == mock_model_instance
