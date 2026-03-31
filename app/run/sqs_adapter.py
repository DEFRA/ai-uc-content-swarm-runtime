"""Job queue adapter for publishing swarm run jobs."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import types_boto3_sqs

from app.config import SwarmInvokeQueueConfig

logger = logging.getLogger(__name__)


@dataclass
class SwarmRunJob:
    """Job message to be sent to the queue."""

    run_id: str
    name: str
    context_documents: list[dict]
    task: str = field(default="generate_content")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "task": self.task,
            "name": self.name,
            "context_documents": self.context_documents,
        }


class AbstractJobPublisher(ABC):
    """Abstract interface for publishing jobs to a queue."""

    @abstractmethod
    async def publish_job(self, job: SwarmRunJob) -> None:
        """Publish a job to the queue.

        Args:
            job: The SwarmRunJob to publish.
        """


class SqsAdapter(AbstractJobPublisher):
    """SQS-backed job queue adapter using an injected boto3 SQS client and typed queue config."""

    def __init__(
        self,
        sqs_client: types_boto3_sqs.SQSClient,
        swarm_invoke_queue: SwarmInvokeQueueConfig,
    ) -> None:
        """Initialize the SQS adapter.

        Args:
            sqs_client: Injected boto3 SQS client.
            swarm_invoke_queue: Typed swarm invoke queue configuration.
        """
        self.client = sqs_client
        self.queue_url = swarm_invoke_queue.url
        self._queue_config = swarm_invoke_queue

    async def publish_job(self, job: SwarmRunJob) -> None:
        """Publish a job to the SQS queue asynchronously.

        Args:
            job: The SwarmRunJob to publish.
        """

        def _send_message() -> None:
            try:
                response = self.client.send_message(
                    QueueUrl=self.queue_url,
                    MessageBody=json.dumps(job.to_dict()),
                )
                logger.info(
                    "Published job %s to queue (MessageId: %s)",
                    job.run_id,
                    response.get("MessageId"),
                )
            except Exception as e:
                logger.error("Failed to publish job %s to queue: %s", job.run_id, e)
                raise

        await asyncio.to_thread(_send_message)
