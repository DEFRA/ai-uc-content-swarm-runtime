from pydantic_ai.models import bedrock as bedrock_models
from pydantic_ai.providers import bedrock as bedrock_providers

from app import config

settings = config.get_config()

provider = bedrock_providers.BedrockProvider(region_name=settings.aws_region)


def _setup_model(
    model_config: config.BedrockModelConfig,
) -> bedrock_models.BedrockConverseModel:
    """Create a BedrockConverseModel from configuration."""
    guardrails = model_config.guardrails

    settings = (
        bedrock_models.BedrockModelSettings(
            bedrock_guardrail_config={
                "guardrailIdentifier": guardrails.id,
                "guardrailVersion": guardrails.version,
                "trace": "enabled",
            }
        )
        if guardrails
        else None
    )

    if guardrails:
        settings = bedrock_models.BedrockModelSettings(
            bedrock_guardrail_config={
                "guardrailIdentifier": guardrails.id,
                "guardrailVersion": guardrails.version,
                "trace": "enabled",
            }
        )

    return bedrock_models.BedrockConverseModel(
        model_config.inference_profile,
        provider=provider,
        profile=provider.model_profile(model_config.model_id),
        settings=settings,
    )


claude_haiku = _setup_model(settings.bedrock.claude_haiku)

claude_sonnet = _setup_model(settings.bedrock.claude_sonnet)
