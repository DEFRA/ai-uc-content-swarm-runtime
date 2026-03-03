import logging
from typing import Annotated, Type

import pydantic
import pydantic_settings

logger = logging.getLogger(__name__)


class BedrockGuardrailConfig(pydantic.BaseModel):
    id: str = pydantic.Field(
        ...,
        pattern=r"^(|([a-z0-9-:.]+)|(arn:aws(-[^:]+)?:bedrock:[a-z0-9-]{1,20}:[0-9]{12}:guardrail/[a-z0-9-:.]+))$",
    )
    version: str = pydantic.Field(..., pattern=r"^(([1-9][0-9]{0,7})|DRAFT)$")


class BedrockModelConfig(pydantic.BaseModel):
    model_id: str
    inference_profile: str = pydantic.Field(
        ...,
        pattern=r"^((arn:aws:bedrock:(|[0-9a-z-]{0,20}):(|[0-9]{12}):(inference-profile|application-inference-profile)/[a-zA-Z0-9-:.]+)|([a-zA-Z0-9-:.]+))$",
    )
    guardrails: BedrockGuardrailConfig | None = None


class BedrockConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict()
    claude_haiku: Annotated[BedrockModelConfig, pydantic_settings.NoDecode] = pydantic.Field(
        ..., validation_alias="CLAUDE_HAIKU_MODEL_CONFIG"
    )
    claude_sonnet: Annotated[BedrockModelConfig, pydantic_settings.NoDecode] = pydantic.Field(
        ..., validation_alias="CLAUDE_SONNET_MODEL_CONFIG"
    )

    @pydantic.field_validator("claude_haiku", "claude_sonnet", mode="before")
    @classmethod
    def _parse_bedrock_model_config(
        cls: Type["BedrockConfig"], v: str) -> BedrockModelConfig:
        if not isinstance(v, str):
            raise ValueError("Bedrock model config must be a string")

        s = v.strip()

        parts = [p.strip() for p in s.split(",")]

        (model_id, inference_profile) = parts[0:2]

        guardrails = None

        if len(parts) > 2:
            (guardrail_id, guardrail_version) = parts[2].split(":")

            guardrails = BedrockGuardrailConfig(
                id=guardrail_id,
                version=guardrail_version,
            )

        try:
            return BedrockModelConfig(
                model_id=model_id,
                inference_profile=inference_profile,
                guardrails=guardrails,
            )
        except pydantic.ValidationError as e:
            msg = f"invalid Bedrock model config: {e}"
            raise ValueError(msg) from e


class AppConfig(pydantic_settings.BaseSettings):
    model_config = pydantic_settings.SettingsConfigDict()
    python_env: str | None = None
    host: str = "127.0.0.1"
    port: int = 8086
    log_config: str | None = None
    mongo_uri: str | None = None
    mongo_database: str = "ai-uc-content-swarm-runtime"
    mongo_truststore: str = "TRUSTSTORE_CDP_ROOT_CA"
    localstack_endpoint_url: str | None = None
    http_proxy: pydantic.HttpUrl | None = None
    enable_metrics: bool = False
    tracing_header: str = "x-cdp-request-id"

    bedrock: BedrockConfig = BedrockConfig()  # type: ignore


config: AppConfig | None = None


def get_config() -> AppConfig:
    global config

    if config is not None:
        return config

    try:
        config = AppConfig()

        return config
    except pydantic.ValidationError as e:
        error_details = [
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "type": error["type"],
                "message": error["msg"],
                "url": error.get("url"),
            }
            for error in e.errors()
        ]

        error_strings = [
            f"Field '{error['field']}' {error['message']}" for error in error_details
        ]

        msg = f"Config validation failed with errors: {', '.join(error_strings)}"
        logger.error(msg)
        raise RuntimeError(msg) from None
