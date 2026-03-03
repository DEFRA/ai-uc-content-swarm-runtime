import boto3
from pydantic_ai.models import bedrock as bedrock_models
from pydantic_ai.providers import bedrock as bedrock_providers

from app import config

settings: config.AppConfig = config.get_config()

bedrock_runtime = boto3.client(
    "bedrock-runtime",
    region_name=settings.aws.region_name,
    aws_account_id=settings.aws.account_id,
)


def _setup_model_settings(
    guardrails: config.BedrockGuardrailConfig,
) -> bedrock_models.BedrockModelSettings | None:
    if guardrails is None:
        return None

    if guardrails.id is None or guardrails.version is None:
        return None

    return bedrock_models.BedrockModelSettings(
        guardrails=[
            bedrock_models.BedrockGuardrail(
                id=guardrails.id,
                version=guardrails.version,
            )
        ]
    )


provider = bedrock_providers.BedrockProvider(bedrock_client=bedrock_runtime)

haiku_config = settings.bedrock.claude_haiku
sonnet_config = settings.bedrock.claude_sonnet

claude_haiku_settings: bedrock_models.BedrockModelSettings | None = (
    _setup_model_settings(haiku_config.guardrails)
)
claude_sonnet_settings: bedrock_models.BedrockModelSettings | None = (
    _setup_model_settings(sonnet_config.guardrails)
)

claude_haiku = bedrock_models.BedrockConverseModel(
    settings.bedrock.claude_haiku.inference_profile,
    provider=provider,
    profile=provider.model_profile(settings.bedrock.claude_haiku.model_id),
    settings=claude_haiku_settings,
)

print(claude_haiku.model_name)

claude_sonnet = bedrock_models.BedrockConverseModel(
    settings.bedrock.claude_sonnet.inference_profile,
    provider=provider,
    profile=provider.model_profile(settings.bedrock.claude_sonnet.model_id),
    settings=claude_sonnet_settings,
)
