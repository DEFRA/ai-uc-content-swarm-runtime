from typing import Annotated

import boto3
import fastapi
import types_boto3_sqs

from app import config
from app.run import dependencies as run_dependencies
from app.swarm import runner, sqs
from app.swarm.content_pages import repository as content_pages_repo
from app.swarm.context import repository as context_repo


def get_swarm_runner(
    result_handler: Annotated[
        runner.RunResultHandler, fastapi.Depends(run_dependencies.get_run_service)
    ],
) -> runner.SwarmRunner:
    return runner.SwarmRunner(
        context_repository=get_s3_context_repository(),
        content_pages_repository=get_s3_content_pages_repository(),
        result_handler=result_handler,
    )


def get_sqs_client() -> types_boto3_sqs.SQSClient:
    app_config = config.get_config()

    return boto3.client(
        "sqs",
        region_name=app_config.aws_region,
        endpoint_url=app_config.sqs.endpoint_url,
    )


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


def get_s3_content_pages_repository() -> content_pages_repo.S3ContentPagesRepository:
    """Provide an S3-backed content pages repository.

    Returns:
        S3ContentPagesRepository initialized with a boto3 S3 client.
    """
    app_config = config.get_config()

    s3_client = boto3.client(
        "s3",
        region_name=app_config.aws_region,
        endpoint_url=app_config.localstack_url,
    )

    return content_pages_repo.S3ContentPagesRepository(
        s3_client=s3_client,
        bucket=app_config.context_bucket,
    )


def get_sqs_listener(
    swarm_runner_instance: runner.SwarmRunner,
) -> sqs.SqsListener:
    """Provide an SqsListener instance.

    Args:
        swarm_runner_instance: The SwarmRunner instance with injected dependencies.

    Returns:
        An SqsListener configured with the queue URL and swarm runner.
    """
    app_config = config.get_config()

    return sqs.SqsListener(
        swarm_invoke_queue=app_config.swarm_invoke_queue,
        sqs_client=get_sqs_client(),
        swarm_runner=swarm_runner_instance,
    )
