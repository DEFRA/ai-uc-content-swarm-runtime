import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fastapi
import pytest

from app.run import models as run_models
from app.run.context import api_schemas
from app.run.context import models as context_models
from app.run.context import router as context_router


@pytest.mark.asyncio
async def test_initiate_context_upload_success() -> None:
    mock_context_service = AsyncMock()
    mock_context_service.initiate_upload = AsyncMock(
        return_value=context_models.UploadInitiation(upload_id="upload-123")
    )

    req = api_schemas.ContextUploadRequest(
        title="My Title", description="desc", redirect="https://example.com"
    )

    res = await context_router.initiate_context_upload(
        "run-1", req, context_service=mock_context_service
    )

    assert res == {"upload_id": "upload-123"}
    mock_context_service.initiate_upload.assert_awaited_once_with("run-1", req)


@pytest.mark.asyncio
async def test_initiate_context_upload_run_not_found() -> None:
    mock_context_service = AsyncMock()
    mock_context_service.initiate_upload = AsyncMock(
        side_effect=run_models.RunNotFoundError("no run")
    )

    req = api_schemas.ContextUploadRequest(title="T", description=None, redirect="r")

    with pytest.raises(fastapi.HTTPException) as exc:
        await context_router.initiate_context_upload(
            "run-1", req, context_service=mock_context_service
        )

    assert exc.value.status_code == fastapi.status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_run_contexts_not_found() -> None:
    mock_run_service = AsyncMock()
    mock_run_service.get_run = AsyncMock(return_value=None)

    response = fastapi.Response()

    with pytest.raises(fastapi.HTTPException) as exc:
        await context_router.get_run_contexts(
            "run-1", response, run_service=mock_run_service
        )

    assert exc.value.status_code == fastapi.status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_get_run_contexts_no_contexts() -> None:
    mock_run_service = AsyncMock()
    mock_run_service.get_run = AsyncMock(return_value=SimpleNamespace(contexts=[]))

    response = fastapi.Response()
    res = await context_router.get_run_contexts(
        "run-1", response, run_service=mock_run_service
    )

    assert response.status_code == fastapi.status.HTTP_204_NO_CONTENT
    assert res == []


@pytest.mark.asyncio
async def test_get_run_contexts_with_contexts() -> None:
    mock_run_service = AsyncMock()

    ctx = SimpleNamespace(
        id=uuid.uuid4(),
        filename="file.txt",
        title="T",
        s3_key="key",
        s3_bucket="bucket",
        checksum_sha256="abc",
        status="uploaded",
        created_at=__import__("datetime").datetime.now(),
    )

    mock_run_service.get_run = AsyncMock(return_value=SimpleNamespace(contexts=[ctx]))

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


@pytest.mark.asyncio
async def test_handle_callback_delegates_to_service() -> None:
    mock_context_service = AsyncMock()
    mock_context_service.handle_upload_callback = AsyncMock()

    payload = api_schemas.CdpUploaderStatusPayload(upload_status="uploaded")
    cid = str(uuid.uuid4())

    await context_router.handle_callback(
        "run-1", cid, payload, context_service=mock_context_service
    )

    mock_context_service.handle_upload_callback.assert_awaited_once_with(
        payload, run_id="run-1", context_id=uuid.UUID(cid)
    )
