import os

# Bedrock model configs (required by BedrockConfig validators)
os.environ.setdefault("CLAUDE_HAIKU_MODEL_CONFIG", "modelA,profileA")
os.environ.setdefault("CLAUDE_SONNET_MODEL_CONFIG", "modelB,profileB")

# AppConfig environment defaults (use the same names pydantic-settings will look up)
os.environ.setdefault("PYTHON_ENV", "test")
os.environ.setdefault("AWS_REGION", "eu-west-2")
os.environ.setdefault("HOST", "127.0.0.1")
os.environ.setdefault("PORT", "8086")
os.environ.setdefault("HOST_URL", "http://localhost:8086")
os.environ.setdefault("LOG_CONFIG", "")
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DATABASE", "ai-uc-content-swarm-runtime")
os.environ.setdefault("MONGO_TRUSTSTORE", "TRUSTSTORE_CDP_ROOT_CA")
os.environ.setdefault("LOCALSTACK_ENDPOINT_URL", "")
os.environ.setdefault("ENABLE_METRICS", "false")
os.environ.setdefault("TRACING_HEADER", "x-cdp-request-id")
os.environ.setdefault("CDP_UPLOADER_BASE_URL", "http://localhost:8000")
os.environ.setdefault("CONTEXT_BUCKET", "ai-uc-content-swarm-context")
os.environ.setdefault(
    "SWARM_INVOKE_QUEUE_URL",
    "http://sqs.eu-west-2.127.0.0.1:4566/000000000000/ai_content_swarm_invoke",
)
