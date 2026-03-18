"""Tests for S3ContentPagesRepository."""

import boto3
import pytest
import types_boto3_s3
from moto import mock_aws

from app.swarm.content_pages import repository

BUCKET = "ai-uc-content-swarm-content-pages"


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


@pytest.mark.asyncio
async def test_save_and_get_page_success(s3_client: types_boto3_s3.S3Client) -> None:
    """Saving a page then retrieving it returns the original content."""
    repo = repository.S3ContentPagesRepository(s3_client=s3_client, bucket=BUCKET)

    await repo.save_page("run-1", "main", "Main content")
    content = await repo.get_page("run-1", "main")

    assert content == "Main content"


@pytest.mark.asyncio
async def test_get_page_missing_raises_not_found(
    s3_client: types_boto3_s3.S3Client,
) -> None:
    """Requesting a non-existent page raises ContentPageNotFoundError."""
    repo = repository.S3ContentPagesRepository(s3_client=s3_client, bucket=BUCKET)

    with pytest.raises(repository.ContentPageNotFoundError):
        await repo.get_page("run-1", "missing")


@pytest.mark.asyncio
async def test_list_pages_returns_saved_keys(
    s3_client: types_boto3_s3.S3Client,
) -> None:
    """List pages returns saved page keys without path prefix or .md suffix."""
    repo = repository.S3ContentPagesRepository(s3_client=s3_client, bucket=BUCKET)

    await repo.save_page("run-1", "main", "Main")
    await repo.save_page("run-1", "sub/related", "Related")

    pages = await repo.list_pages("run-1")

    assert "main" in pages
    assert "sub/related" in pages


@pytest.mark.asyncio
async def test_general_s3_error_raises_content_pages_repository_error(
    s3_client: types_boto3_s3.S3Client,
) -> None:
    """A general S3 error is wrapped as ContentPagesRepositoryError."""
    repo = repository.S3ContentPagesRepository(s3_client=s3_client, bucket=BUCKET)

    # Simulate a general S3 error by pointing at a non-existent bucket.
    repo.bucket = "invalid-bucket-name"

    with pytest.raises(repository.ContentPagesRepositoryError) as err:
        await repo.get_page("run-1", "some/page")

    assert isinstance(err.value.__cause__, s3_client.exceptions.NoSuchBucket)
