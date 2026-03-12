import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import fastapi
import pytest
from pytest_mock import MockerFixture

from app.run import models as run_models
from app.run import service as run_service_module
from app.run.context import api_schemas
from app.run.context import models as context_models
from app.run.context import router as context_router
from app.run.context import service as context_service_module


class TestInitiateContextUpload:
    """Tests for the initiate_context_upload endpoint."""

    @pytest.fixture
    def mock_context_service(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock ContextService."""
        return mocker.AsyncMock(spec=context_service_module.ContextService)  # type: ignore[no-any-return]

    @pytest.fixture
    def upload_request(self) -> api_schemas.ContextUploadRequest:
        """Create a sample ContextUploadRequest."""
        return api_schemas.ContextUploadRequest(
            title="My Title", description="desc", redirect="https://example.com"
        )

    @pytest.mark.asyncio
    async def test_returns_upload_id_on_success(
        self,
        mock_context_service: AsyncMock,
        upload_request: api_schemas.ContextUploadRequest,
    ) -> None:
        """Test that a successful upload returns the upload_id."""
        mock_context_service.initiate_upload.return_value = (
            context_models.UploadInitiation(upload_id="upload-123")
        )

        res = await context_router.initiate_context_upload(
            "run-1", upload_request, context_service=mock_context_service
        )

        assert res == api_schemas.CdpUploaderInitiateResponse(uploadId="upload-123")
        mock_context_service.initiate_upload.assert_awaited_once_with(
            "run-1", upload_request
        )

    @pytest.mark.asyncio
    async def test_raises_404_when_run_not_found(
        self,
        mock_context_service: AsyncMock,
        upload_request: api_schemas.ContextUploadRequest,
    ) -> None:
        """Test that RunNotFoundError is converted to a 404 HTTP exception."""
        mock_context_service.initiate_upload.side_effect = run_models.RunNotFoundError(
            "no run"
        )

        with pytest.raises(fastapi.HTTPException) as exc:
            await context_router.initiate_context_upload(
                "run-1", upload_request, context_service=mock_context_service
            )

        assert exc.value.status_code == fastapi.status.HTTP_404_NOT_FOUND


class TestGetRunContexts:
    """Tests for the get_run_contexts endpoint."""

    @pytest.fixture
    def mock_run_service(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock RunService."""
        return mocker.AsyncMock(spec=run_service_module.RunService)  # type: ignore[no-any-return]

    @pytest.fixture
    def sample_run_with_context(self) -> run_models.Run:
        """Create a Run with one ContextMetadata attached."""
        now = datetime.now(tz=UTC)
        run = run_models.Run(
            id="run-1",
            name="Test Run",
            status=run_models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )
        run.add_context(
            context_models.ContextMetadata(
                id=uuid.uuid4(),
                title="T",
                s3_bucket="bucket",
                s3_key="key",
                filename="file.txt",
                checksum_sha256="abc",
                status="uploaded",
                created_at=now,
            )
        )
        return run

    @pytest.mark.asyncio
    async def test_raises_404_when_run_not_found(
        self, mock_run_service: AsyncMock
    ) -> None:
        """Test that a missing run raises a 404 HTTP exception."""
        mock_run_service.get_run.return_value = None

        with pytest.raises(fastapi.HTTPException) as exc:
            await context_router.get_run_contexts(
                "run-1", fastapi.Response(), run_service=mock_run_service
            )

        assert exc.value.status_code == fastapi.status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_returns_204_when_no_contexts(
        self, mock_run_service: AsyncMock
    ) -> None:
        """Test that a run with no contexts returns 204 and an empty list."""
        now = datetime.now(tz=UTC)
        mock_run_service.get_run.return_value = run_models.Run(
            id="run-1",
            name="Test Run",
            status=run_models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        response = fastapi.Response()
        res = await context_router.get_run_contexts(
            "run-1", response, run_service=mock_run_service
        )

        assert response.status_code == fastapi.status.HTTP_204_NO_CONTENT
        assert res == []

    @pytest.mark.asyncio
    async def test_returns_contexts_for_run(
        self,
        mock_run_service: AsyncMock,
        sample_run_with_context: run_models.Run,
    ) -> None:
        """Test that contexts are returned and mapped to the response schema."""
        mock_run_service.get_run.return_value = sample_run_with_context
        ctx = sample_run_with_context.contexts[0]

        response = fastapi.Response()
        res = await context_router.get_run_contexts(
            "run-1", response, run_service=mock_run_service
        )

        assert len(res) == 1
        assert res[0].id == ctx.id
        assert res[0].filename == ctx.filename
        assert res[0].title == ctx.title
        assert res[0].s3_key == ctx.s3_key
        assert res[0].s3_bucket == ctx.s3_bucket
        assert res[0].checksum_sha256 == ctx.checksum_sha256
        assert res[0].status == ctx.status


class TestHandleCallback:
    """Tests for the handle_callback endpoint."""

    @pytest.fixture
    def mock_context_service(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock ContextService."""
        return mocker.AsyncMock(spec=context_service_module.ContextService)  # type: ignore[no-any-return]

    @pytest.mark.asyncio
    async def test_delegates_to_context_service(
        self, mock_context_service: AsyncMock
    ) -> None:
        """Test that the callback is forwarded to the context service."""
        payload = api_schemas.CdpUploaderStatusPayload(uploadStatus="uploaded")
        cid = str(uuid.uuid4())

        await context_router.handle_callback(
            "run-1", cid, payload, context_service=mock_context_service
        )

        mock_context_service.handle_upload_callback.assert_awaited_once_with(
            payload, run_id="run-1", context_id=uuid.UUID(cid)
        )
