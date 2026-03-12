import boto3

from app import config
from app.swarm import runner
from app.swarm.context import repository as context_repo


def get_swarm_runner() -> runner.SwarmRunner:
    context_repository = get_s3_context_repository()
    return runner.SwarmRunner(context_repository=context_repository)


def get_s3_context_repository() -> context_repo.S3ContextRepository:
    """Provide an S3-backed context repository.

    Returns:
        S3ContextRepository initialized with a boto3 S3 client.
    """
    app_config = config.get_config()

    s3_client = boto3.client(
        "s3",
        region_name=app_config.aws_region,
        endpoint_url=app_config.localstack_url,
    )

    return context_repo.S3ContextRepository(
        s3_client=s3_client,
        bucket=app_config.context_bucket,
    )
