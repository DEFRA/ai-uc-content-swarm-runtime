from typing import Annotated

import boto3
import fastapi
import types_boto3_sqs
from pymongo.asynchronous.database import AsyncDatabase

import app.common.mongo as mongo
import app.config as app_config
import app.run.repository as repository
import app.run.service as run_service
import app.run.sqs_adapter as sqs_adapter


def get_run_repository(
    db: AsyncDatabase = fastapi.Depends(mongo.get_db),
) -> repository.RunRepository:
    """Provide a RunRepository instance.

    Args:
        db: The AsyncDatabase instance (injected).

    Returns:
        A RunRepository instance backed by MongoDB.
    """
    return repository.MongoRunRepository(db)


def get_sqs_client() -> types_boto3_sqs.SQSClient:
    """Provide a boto3 SQS client.

    Returns:
        A boto3 SQS client configured with AWS settings.
    """
    config = app_config.get_config()

    return boto3.client(
        "sqs",
        region_name=config.aws_region,
        endpoint_url=config.sqs.endpoint_url,
    )


def get_sqs_adapter(
    sqs_client: Annotated[types_boto3_sqs.SQSClient, fastapi.Depends(get_sqs_client)],
) -> sqs_adapter.AbstractJobPublisher:
    """Provide a job queue adapter.

    Args:
        sqs_client: The SQS client instance (injected).

    Returns:
        A JobQueue adapter (SQS implementation).
    """
    config = app_config.get_config()
    return sqs_adapter.SqsAdapter(
        sqs_client=sqs_client, swarm_invoke_queue=config.swarm_invoke_queue
    )


def get_run_service(
    run_repository: Annotated[
        repository.RunRepository, fastapi.Depends(get_run_repository)
    ],
    sqs: Annotated[sqs_adapter.AbstractJobPublisher, fastapi.Depends(get_sqs_adapter)],
) -> run_service.RunService:
    """Provide a RunService instance.

    Args:
        run_repository: The RunRepository instance (injected).
        sqs: The job queue adapter instance (injected).

    Returns:
        A RunService instance.
    """
    return run_service.RunService(run_repository, sqs)
