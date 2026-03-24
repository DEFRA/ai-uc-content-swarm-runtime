"""Tests for SQS integration in the swarm module."""

from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from app.run.models import RunStatus
from app.swarm import models as swarm_models
from app.swarm import runner


class TestSwarmJob:
    """Tests for SwarmJob deserialization."""

    def test_from_message_body_deserializes_valid_message(self) -> None:
        """Test that SwarmJob.from_message_body deserializes JSON correctly."""
        body = '{"run_id": "run-123", "task": "write article", "name": "Test Run", "context_documents": [{"id": "doc-1", "name": "Doc 1", "description": "First", "path": "s3://bucket/doc-1"}, {"id": "doc-2", "name": "Doc 2", "description": "Second", "path": "s3://bucket/doc-2"}]}'

        job = swarm_models.SwarmJob.from_message_body(body)

        assert job.run_id == "run-123"
        assert job.task == "write article"
        assert job.name == "Test Run"
        assert len(job.context_documents) == 2
        assert job.context_documents[0]["id"] == "doc-1"
        assert job.context_documents[1]["id"] == "doc-2"

    def test_from_message_body_handles_missing_context_documents(self) -> None:
        """Test that SwarmJob handles missing context_documents field."""
        body = '{"run_id": "run-456", "task": "research", "name": "Research Run"}'

        job = swarm_models.SwarmJob.from_message_body(body)

        assert job.run_id == "run-456"
        assert job.context_documents == []


class TestSwarmJobHandler:
    """Tests for SwarmJobHandler."""

    @pytest.fixture
    def mock_swarm_runner(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock SwarmRunner."""
        return mocker.AsyncMock(spec=runner.SwarmRunner)

    @pytest.fixture
    def mock_result_handler(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock RunResultHandler."""
        return mocker.AsyncMock(spec=runner.RunResultHandler)

    @pytest.fixture
    def job_handler(
        self, mock_swarm_runner: AsyncMock, mock_result_handler: AsyncMock
    ) -> runner.SwarmJobHandler:
        """Create a SwarmJobHandler with mocked dependencies."""
        return runner.SwarmJobHandler(
            swarm_runner_instance=mock_swarm_runner,
            run_result_handler=mock_result_handler,
        )

    @pytest.mark.asyncio
    async def test_handle_job_invokes_swarm_runner_with_correct_config(
        self,
        job_handler: runner.SwarmJobHandler,
        mock_swarm_runner: AsyncMock,
        mock_result_handler: AsyncMock,
    ) -> None:
        """Test that handle_job invokes SwarmRunner with the correct RunConfig."""
        mock_swarm_runner.start_run.return_value = "execution result"
        mock_result_handler.update_status.return_value = None

        job = swarm_models.SwarmJob(
            run_id="run-1",
            task="write content",
            name="Test Run",
            context_documents=[
                {
                    "id": "12345678-1234-5678-1234-567812345678",
                    "name": "Doc A",
                    "description": "Desc",
                    "path": "s3://bucket/doc-a",
                }
            ],
        )

        await job_handler.handle_job(job)

        mock_swarm_runner.start_run.assert_called_once()
        call_args = mock_swarm_runner.start_run.call_args
        config = call_args[0][0]

        assert isinstance(config, swarm_models.RunConfig)
        assert config.id == "run-1"
        assert config.task == "write content"
        assert config.name == "Test Run"

    @pytest.mark.asyncio
    async def test_handle_job_emits_status_updates(
        self,
        job_handler: runner.SwarmJobHandler,
        mock_swarm_runner: AsyncMock,
        mock_result_handler: AsyncMock,
    ) -> None:
        """Test that handle_job emits status updates through the handler."""
        mock_swarm_runner.start_run.return_value = "final execution result"
        mock_result_handler.update_status.return_value = None

        job = swarm_models.SwarmJob(
            run_id="run-xyz",
            task="analyze",
            name="Analysis Run",
            context_documents=[],
        )

        await job_handler.handle_job(job)

        # Verify status updates were sent
        assert mock_result_handler.update_status.call_count == 2
        calls = mock_result_handler.update_status.call_args_list

        # First call should be RUNNING
        assert calls[0][0] == ("run-xyz", RunStatus.RUNNING)
        # Second call should be COMPLETED
        assert calls[1][0] == ("run-xyz", RunStatus.COMPLETED)

    @pytest.mark.asyncio
    async def test_handle_job_propagates_runner_error(
        self,
        job_handler: runner.SwarmJobHandler,
        mock_swarm_runner: AsyncMock,
        mock_result_handler: AsyncMock,
    ) -> None:
        """Test that exceptions from SwarmRunner propagate up and ERROR status is sent."""
        test_error = ValueError("Swarm execution failed")
        mock_swarm_runner.start_run.side_effect = test_error
        mock_result_handler.update_status.return_value = None

        job = swarm_models.SwarmJob(
            run_id="run-fail",
            task="failing task",
            name="Failing Run",
            context_documents=[],
        )

        with pytest.raises(ValueError, match="Swarm execution failed"):
            await job_handler.handle_job(job)

        # Verify RUNNING was called, then ERROR
        assert mock_result_handler.update_status.call_count == 2
        calls = mock_result_handler.update_status.call_args_list
        assert calls[0][0] == ("run-fail", RunStatus.RUNNING)
        assert calls[1][0] == ("run-fail", RunStatus.ERROR)

    @pytest.mark.asyncio
    async def test_handle_job_propagates_result_handler_error(
        self,
        job_handler: runner.SwarmJobHandler,
        mock_swarm_runner: AsyncMock,
        mock_result_handler: AsyncMock,
    ) -> None:
        """Test that exceptions from result_handler propagate up."""
        mock_swarm_runner.start_run.return_value = "some result"
        handler_error = RuntimeError("Failed to update status")
        # Simulation: RUNNING status update succeeds, but COMPLETED fails, and ERROR also succeeds
        mock_result_handler.update_status.side_effect = [None, handler_error, None]

        job = swarm_models.SwarmJob(
            run_id="run-store-fail",
            task="task",
            name="Run",
            context_documents=[],
        )

        with pytest.raises(RuntimeError, match="Failed to update status"):
            await job_handler.handle_job(job)

        # Verify that ERROR status was attempted after the failed COMPLETED call
        assert mock_result_handler.update_status.call_count == 3
        calls = mock_result_handler.update_status.call_args_list
        assert calls[0][0] == ("run-store-fail", RunStatus.RUNNING)
        assert calls[1][0] == ("run-store-fail", RunStatus.COMPLETED)
        assert calls[2][0] == ("run-store-fail", RunStatus.ERROR)

    @pytest.mark.asyncio
    async def test_handle_job_logs_execution_steps(
        self,
        job_handler: runner.SwarmJobHandler,
        mock_swarm_runner: AsyncMock,
        mock_result_handler: AsyncMock,
        mocker: MockerFixture,
    ) -> None:
        """Test that handle_job logs each step of execution."""
        mock_swarm_runner.start_run.return_value = "result"
        mock_result_handler.update_status.return_value = None
        mock_logger = mocker.patch("app.swarm.runner.logger")

        job = swarm_models.SwarmJob(
            run_id="run-log",
            task="logging test",
            name="Log Test",
            context_documents=[],
        )

        await job_handler.handle_job(job)

        # Verify logging calls
        assert mock_logger.info.call_count >= 3
        call_args_list = [call[0][0] for call in mock_logger.info.call_args_list]

        assert "Handling swarm job for run %s" in call_args_list
        assert "Starting swarm execution for run %s with task: %s" in call_args_list
        assert "Swarm execution completed for run %s" in call_args_list
        assert "Status updated to COMPLETED for run %s" in call_args_list
