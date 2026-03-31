import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import pydantic
import types_boto3_sqs

from app.config import SwarmInvokeQueueConfig
from app.swarm import models as swarm_models
from app.swarm import runner as swarm_runner

logger = logging.getLogger(__name__)


class SQSMessage(pydantic.BaseModel):
    """Validated SQS message structure."""

    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    message_id: str = pydantic.Field(
        ..., alias="MessageId", description="Unique message identifier"
    )
    body: str = pydantic.Field(..., alias="Body", description="Message body content")
    receipt_handle: str = pydantic.Field(
        ..., alias="ReceiptHandle", description="Handle for deleting message"
    )

    # Optional fields that SQS may include
    attributes: dict[str, Any] | None = pydantic.Field(default=None, alias="Attributes")
    message_attributes: dict[str, Any] | None = pydantic.Field(
        default=None, alias="MessageAttributes"
    )
    md5_of_body: str | None = pydantic.Field(default=None, alias="MD5OfBody")


class AbstractQueueListener(ABC):
    """Abstract base for queue listeners."""

    @abstractmethod
    async def start(self) -> None:
        """Start listening for messages from the queue."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop listening for messages."""


class SqsListener(AbstractQueueListener):
    """SQS listener that polls for messages and processes swarm jobs.

    Accepts typed queue and SQS configuration objects.
    """

    def __init__(
        self,
        swarm_invoke_queue: SwarmInvokeQueueConfig,
        sqs_client: types_boto3_sqs.SQSClient,
        swarm_runner: swarm_runner.SwarmRunner,
    ) -> None:
        """Initialize the SQS listener.

        Args:
            swarm_invoke_queue: Typed swarm invoke queue configuration.
            sqs_client: An initialized boto3 SQS client.
            swarm_runner: SwarmRunner instance for executing jobs.
        """
        self.queue_url = swarm_invoke_queue.url
        self.swarm_runner = swarm_runner
        self.poll_interval = swarm_invoke_queue.polling_interval
        self.max_messages = swarm_invoke_queue.batch_size
        self.wait_time = swarm_invoke_queue.wait_time
        self.is_running = False

        self.sqs_client = sqs_client

    async def start(self) -> None:
        """Start the listener polling loop."""
        self.is_running = True

        logger.info("SQS listener starting for queue: %s", self.queue_url)

        while self.is_running:
            try:
                await self._poll_messages()
            except Exception as e:
                logger.exception("Unexpected error in polling SQS messages: %s", e)
            finally:
                await asyncio.sleep(self.poll_interval)

    async def stop(self) -> None:
        """Stop the listener."""
        self.is_running = False
        logger.info("SQS listener stopped")

    async def _poll_messages(self) -> None:
        """Poll for messages from the queue."""

        def _receive_messages() -> list[Any]:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.max_messages,
                WaitTimeSeconds=self.wait_time,
            )

            return response.get("Messages", [])

        try:
            messages = await asyncio.to_thread(_receive_messages)

            for message in messages:
                await self._handle_message(message)
        except Exception as e:
            logger.exception("Error polling messages from queue: %s", e)

    async def _handle_message(self, message: dict[str, Any]) -> None:
        """Process a single message from the queue.

        Args:
            message: The SQS message dictionary.
        """
        try:
            sqs_message = SQSMessage(**message)
            job = swarm_models.SwarmJob.from_message_body(sqs_message.body)

            logger.info("Processing swarm job for run %s", job.run_id)

            try:
                await self.swarm_runner.handle_job(job)
            finally:
                await self._delete_message(sqs_message.receipt_handle)

            logger.info("Completed swarm job for run %s", job.run_id)
        except Exception as e:
            logger.exception("Failed to process message: %s", e)

    async def _delete_message(self, receipt_handle: str) -> None:
        """Delete a message from the queue.

        Args:
            receipt_handle: The receipt handle from SQS.
        """

        def _delete() -> None:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle,
            )

        await asyncio.to_thread(_delete)
