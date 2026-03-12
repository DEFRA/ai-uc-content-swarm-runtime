"""Tests for S3ContextRepository."""

import boto3
import pytest
import types_boto3_s3
from moto import mock_aws

from app.swarm.context import repository

BUCKET = "ai-uc-content-swarm-context"


@pytest.fixture
def s3_client():
    """Provide a moto-backed S3 client with a pre-created bucket."""
    with mock_aws():
        client = boto3.client("s3", region_name="eu-west-2")
        client.create_bucket(
            Bucket=BUCKET,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-2"},
        )
        yield client


class TestS3ContextRepositoryGetContext:
    """Test S3ContextRepository.get_context()."""

    @pytest.mark.asyncio
    async def test_get_context_success(
        self, s3_client: types_boto3_s3.S3Client
    ) -> None:
        """Test retrieving a context document."""
        s3_client.put_object(
            Bucket=BUCKET, Key="policy/my-policy.txt", Body=b"Policy content here"
        )

        repo = repository.S3ContextRepository(s3_client=s3_client, bucket=BUCKET)

        doc = await repo.get_context("policy/my-policy.txt")

        assert doc == "Policy content here"

    @pytest.mark.asyncio
    async def test_get_context_with_missing_file_raises_error(
        self, s3_client: types_boto3_s3.S3Client
    ) -> None:
        """Test that requesting a non-existent context raises ContextNotFoundError."""
        repo = repository.S3ContextRepository(s3_client=s3_client, bucket=BUCKET)

        with pytest.raises(repository.ContextNotFoundError):
            await repo.get_context("nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_get_context_general_error_raises_context_repository_error(
        self, s3_client: types_boto3_s3.S3Client
    ) -> None:
        """Test that a general error raises ContextRepositoryError."""
        repo = repository.S3ContextRepository(s3_client=s3_client, bucket=BUCKET)

        # Simulate an S3 error by using an invalid bucket name
        repo.bucket = "invalid-bucket-name"

        with pytest.raises(repository.ContextRepositoryError) as err:
            await repo.get_context("some/file.txt")

        assert isinstance(err.value.__cause__, s3_client.exceptions.NoSuchBucket)
