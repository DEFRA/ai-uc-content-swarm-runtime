"""Tests for SqsAdapter job publishing."""

import json

import boto3
import pytest
import types_boto3_sqs
from moto import mock_aws

from app.config import SwarmInvokeQueueConfig
from app.run import sqs_adapter


@pytest.fixture
def sqs_client_and_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[types_boto3_sqs.SQSClient, str]:
    """Provide a moto-backed SQS client with a pre-created queue."""
    with mock_aws():
        client = boto3.client("sqs", region_name="eu-west-2")
        response = client.create_queue(QueueName="test-swarm-invoke-queue")
        queue_url = response["QueueUrl"]
        monkeypatch.setenv("SWARM_INVOKE_QUEUE_URL", queue_url)
        yield client, queue_url


@pytest.mark.asyncio
async def test_publish_job_sends_message_to_queue(
    sqs_client_and_queue: tuple[types_boto3_sqs.SQSClient, str],
) -> None:
    """Publishing a job sends a message to the SQS queue."""
    sqs_client, queue_url = sqs_client_and_queue

    queue_config = SwarmInvokeQueueConfig(url=queue_url)
    adapter = sqs_adapter.SqsAdapter(
        sqs_client=sqs_client, swarm_invoke_queue=queue_config
    )

    job = sqs_adapter.SwarmRunJob(
        run_id="run-123",
        task="write article",
        name="Test Run",
        context_documents=[
            {
                "id": "doc-1",
                "name": "Doc 1",
                "description": "First document",
                "path": "s3://bucket/doc-1",
            },
            {
                "id": "doc-2",
                "name": "Doc 2",
                "description": "Second document",
                "path": "s3://bucket/doc-2",
            },
        ],
    )

    await adapter.publish_job(job)

    response = sqs_client.receive_message(QueueUrl=queue_url)
    messages = response.get("Messages", [])

    assert len(messages) == 1
    message_body = json.loads(messages[0]["Body"])
    assert message_body["run_id"] == "run-123"
    assert message_body["task"] == "write article"
    assert message_body["name"] == "Test Run"
    assert len(message_body["context_documents"]) == 2
    assert message_body["context_documents"][0]["id"] == "doc-1"
    assert message_body["context_documents"][1]["id"] == "doc-2"


@pytest.mark.asyncio
async def test_publish_job_sends_valid_json(
    sqs_client_and_queue: tuple[types_boto3_sqs.SQSClient, str],
) -> None:
    """Message body from published job is valid JSON with all expected keys."""
    sqs_client, queue_url = sqs_client_and_queue

    queue_config = SwarmInvokeQueueConfig(url=queue_url)
    adapter = sqs_adapter.SqsAdapter(
        sqs_client=sqs_client, swarm_invoke_queue=queue_config
    )

    job = sqs_adapter.SwarmRunJob(
        run_id="run-456",
        task="research",
        name="Research Run",
        context_documents=[],
    )

    await adapter.publish_job(job)

    response = sqs_client.receive_message(QueueUrl=queue_url)
    messages = response.get("Messages", [])

    assert len(messages) == 1
    message_body = json.loads(messages[0]["Body"])

    assert "run_id" in message_body
    assert "task" in message_body
    assert "name" in message_body
    assert "context_documents" in message_body
    assert isinstance(message_body["context_documents"], list)


@pytest.mark.asyncio
async def test_publish_job_with_empty_context_document_ids(
    sqs_client_and_queue: tuple[types_boto3_sqs.SQSClient, str],
) -> None:
    """Publishing a job with empty context_documents serialises correctly."""
    sqs_client, queue_url = sqs_client_and_queue

    queue_config = SwarmInvokeQueueConfig(url=queue_url)
    adapter = sqs_adapter.SqsAdapter(
        sqs_client=sqs_client, swarm_invoke_queue=queue_config
    )

    job = sqs_adapter.SwarmRunJob(
        run_id="run-789",
        task="analysis",
        name="Analysis Run",
        context_documents=[],
    )

    await adapter.publish_job(job)

    response = sqs_client.receive_message(QueueUrl=queue_url)
    messages = response.get("Messages", [])

    assert len(messages) == 1
    message_body = json.loads(messages[0]["Body"])
    assert message_body["context_documents"] == []


@pytest.mark.asyncio
async def test_publish_job_multiple_messages(
    sqs_client_and_queue: tuple[types_boto3_sqs.SQSClient, str],
) -> None:
    """Publishing multiple jobs results in multiple queue messages."""
    sqs_client, queue_url = sqs_client_and_queue

    queue_config = SwarmInvokeQueueConfig(url=queue_url)
    adapter = sqs_adapter.SqsAdapter(
        sqs_client=sqs_client, swarm_invoke_queue=queue_config
    )

    job1 = sqs_adapter.SwarmRunJob(
        run_id="run-1",
        task="task 1",
        name="Run 1",
        context_documents=[
            {
                "id": "doc-a",
                "name": "Doc A",
                "description": "Document A",
                "path": "s3://bucket/doc-a",
            }
        ],
    )
    job2 = sqs_adapter.SwarmRunJob(
        run_id="run-2",
        task="task 2",
        name="Run 2",
        context_documents=[
            {
                "id": "doc-b",
                "name": "Doc B",
                "description": "Document B",
                "path": "s3://bucket/doc-b",
            },
            {
                "id": "doc-c",
                "name": "Doc C",
                "description": "Document C",
                "path": "s3://bucket/doc-c",
            },
        ],
    )

    await adapter.publish_job(job1)
    await adapter.publish_job(job2)

    response = sqs_client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=10)
    messages = response.get("Messages", [])

    assert len(messages) == 2

    bodies = [json.loads(msg["Body"]) for msg in messages]
    run_ids = {body["run_id"] for body in bodies}
    assert run_ids == {"run-1", "run-2"}
