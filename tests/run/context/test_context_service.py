import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_mock import MockerFixture

from app.run import models as run_models
from app.run import repository
from app.run.context import api_schemas, models, service


class TestContextService:
    """Tests for ContextService."""

    @pytest.fixture
    def mock_repository(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock RunRepository."""
        return mocker.AsyncMock(spec=repository.RunRepository)  # type: ignore[no-any-return]

    @pytest.fixture
    def context_service(self, mock_repository: AsyncMock) -> service.ContextService:
        """Create a ContextService with mocked repository."""
        return service.ContextService(run_repository=mock_repository)

    @pytest.fixture
    def sample_run(self) -> run_models.Run:
        """Create a sample run for testing."""
        now = datetime.now(tz=UTC)
        return run_models.Run(
            id="run-123",
            name="Test Run",
            status=run_models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

    @pytest.mark.asyncio
    async def test_initiate_upload_creates_pending_context(
        self,
        context_service: service.ContextService,
        mock_repository: AsyncMock,
        sample_run: run_models.Run,
        mocker: MockerFixture,
    ) -> None:
        """Test that initiate_upload creates and persists a pending context."""
        # Setup
        mock_repository.get_run.return_value = sample_run

        mock_response = MagicMock()
        mock_response.json.return_value = {"uploadId": "uploader-id-123"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = None

        mocker.patch(
            "app.run.context.service.http_client.create_async_client",
            return_value=mock_async_client,
        )

        request = api_schemas.ContextUploadRequest(
            title="test.txt",
            description="Test description",
            redirect="http://localhost:8086/redirect",
        )

        # Act
        result = await context_service.initiate_upload("run-123", request)

        # Assert
        assert result.upload_id == "uploader-id-123"

        # Verify repository.append_context was called
        mock_repository.append_context.assert_called_once()
        call_args = mock_repository.append_context.call_args
        assert call_args[0][0] == "run-123"  # run_id

        pending_context = call_args[0][1]  # context argument
        assert pending_context.title == "test.txt"
        assert pending_context.filename is None
        assert pending_context.filename is None
        assert pending_context.description == "Test description"
        assert pending_context.status == "pending"
        assert pending_context.s3_bucket == "ai-uc-content-swarm-context"
        assert pending_context.s3_key is None
        assert pending_context.checksum_sha256 is None

    @pytest.mark.asyncio
    async def test_initiate_upload_includes_context_id_in_callback_url(
        self,
        context_service: service.ContextService,
        mock_repository: AsyncMock,
        sample_run: run_models.Run,
        mocker: MockerFixture,
    ) -> None:
        """Test that initiate_upload passes context_id in callback URL."""
        mock_repository.get_run.return_value = sample_run

        mock_response = MagicMock()
        mock_response.json.return_value = {"uploadId": "uploader-id-456"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        mock_async_client = AsyncMock()
        mock_async_client.__aenter__.return_value = mock_client
        mock_async_client.__aexit__.return_value = None

        mocker.patch(
            "app.run.context.service.http_client.create_async_client",
            return_value=mock_async_client,
        )

        request = api_schemas.ContextUploadRequest(
            title="test.txt",
            description=None,
            redirect="http://localhost:8086/redirect",
        )

        # Act
        await context_service.initiate_upload("run-123", request)

        # Assert
        call_kwargs = mock_client.post.call_args[1]["json"]
        callback_url = call_kwargs["callback"]

        assert "context_id=" not in callback_url
        assert callback_url.startswith("http://localhost:8086/runs/run-123/contexts/")
        assert callback_url.endswith("/callback")

    @pytest.mark.asyncio
    async def test_initiate_upload_raises_when_run_not_found(
        self,
        context_service: service.ContextService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that initiate_upload raises when run doesn't exist."""
        mock_repository.get_run.return_value = None

        request = api_schemas.ContextUploadRequest(
            title="test.txt",
            description="desc",
            redirect="http://localhost:8086/redirect",
        )

        with pytest.raises(run_models.RunNotFoundError):
            await context_service.initiate_upload("nonexistent-run", request)

        mock_repository.append_context.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_upload_callback_with_context_id_updates_pending(
        self,
        context_service: service.ContextService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that handle_upload_callback updates the pending context."""
        # Setup
        now = datetime.now(tz=UTC)
        context_id = uuid.uuid4()

        pending_context = models.ContextMetadata(
            id=context_id,
            title="test.txt",
            s3_bucket="test-bucket",
            s3_key=None,
            checksum_sha256=None,
            filename=None,
            status="pending",
            created_at=now,
            description="Test description",
        )

        run = run_models.Run(
            id="run-123",
            name="Test Run",
            status=run_models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )
        run.add_context(pending_context)

        mock_repository.get_run.return_value = run

        payload = api_schemas.CdpUploaderStatusPayload(
            uploadStatus="success",
            form={
                "file": api_schemas.FileUploadDetail(
                    fileId="file-123",
                    filename="test.txt",
                    fileStatus="uploaded",
                    contentLength=1024,
                    checksumSha256="abc123def456",
                    detectedContentType=None,
                    s3Key="s3/path/to/file",
                    s3Bucket="s3-bucket",
                )
            },
        )

        # Act
        await context_service.handle_upload_callback(
            payload, run_id="run-123", context_id=context_id
        )

        # Assert
        mock_repository.append_context.assert_called_once()
        call_args = mock_repository.append_context.call_args

        updated_context = call_args[0][1]
        assert updated_context.id == context_id
        assert updated_context.filename == "test.txt"
        assert updated_context.s3_key == "s3/path/to/file"
        assert updated_context.s3_bucket == "s3-bucket"
        assert updated_context.checksum_sha256 == "abc123def456"
        assert updated_context.status == "uploaded"
        assert updated_context.description == "Test description"

    @pytest.mark.asyncio
    async def test_handle_upload_callback_raises_when_run_not_found(
        self,
        context_service: service.ContextService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that handle_upload_callback raises when run doesn't exist."""
        mock_repository.get_run.return_value = None

        payload = api_schemas.CdpUploaderStatusPayload(
            uploadStatus="success",
            form={},
        )

        with pytest.raises(run_models.RunNotFoundError):
            await context_service.handle_upload_callback(
                payload, run_id="nonexistent", context_id=uuid.uuid4()
            )

    @pytest.mark.asyncio
    async def test_handle_upload_callback_with_multiple_files_processes_first(
        self,
        context_service: service.ContextService,
        mock_repository: AsyncMock,
    ) -> None:
        """Test that handle_upload_callback processes only the first file."""
        # Setup
        now = datetime.now(tz=UTC)
        context_id = uuid.uuid4()

        pending_context = models.ContextMetadata(
            id=context_id,
            title="test.txt",
            s3_bucket="test-bucket",
            s3_key=None,
            checksum_sha256=None,
            status="pending",
            created_at=now,
        )

        run = run_models.Run(
            id="run-123",
            name="Test Run",
            status=run_models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )
        run.add_context(pending_context)

        mock_repository.get_run.return_value = run

        payload = api_schemas.CdpUploaderStatusPayload(
            uploadStatus="success",
            form={
                "file1": api_schemas.FileUploadDetail(
                    fileId="file-1",
                    filename="test.txt",
                    fileStatus="uploaded",
                    contentLength=1024,
                    checksumSha256="abc123",
                    detectedContentType=None,
                    s3Key="s3/path/file1",
                    s3Bucket="s3-bucket",
                ),
                "file2": api_schemas.FileUploadDetail(
                    fileId="file-2",
                    filename="other.txt",
                    fileStatus="uploaded",
                    contentLength=2048,
                    checksumSha256="def456",
                    detectedContentType=None,
                    s3Key="s3/path/file2",
                    s3Bucket="s3-bucket",
                ),
            },
        )

        # Act
        await context_service.handle_upload_callback(
            payload, run_id="run-123", context_id=context_id
        )

        # Assert - should only update once (process first file and return)
        mock_repository.append_context.assert_called_once()
