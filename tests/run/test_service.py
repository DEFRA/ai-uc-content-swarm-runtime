from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pytest_mock import MockerFixture

from app.run import models, repository, service


class TestRunService:
    """Tests for RunService."""

    @pytest.fixture
    def mock_repository(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock RunRepository based on the ABC."""
        return mocker.AsyncMock(spec=repository.RunRepository)  # type: ignore[no-any-return]

    @pytest.fixture
    def mock_swarm(self, mocker: MockerFixture) -> AsyncMock:
        """Create a mock SwarmRunner."""
        return mocker.AsyncMock()  # type: ignore[no-any-return]

    @pytest.fixture
    def run_service(
        self, mock_repository: AsyncMock, mock_swarm: AsyncMock
    ) -> service.RunService:
        """Create a RunService with mocked dependencies."""
        return service.RunService(run_repository=mock_repository, swarm=mock_swarm)

    @pytest.mark.asyncio
    async def test_setup_run_creates_and_returns_run(
        self, run_service: service.RunService, mock_repository: AsyncMock
    ) -> None:
        """Test that setup_run calls repository and returns created run."""
        now = datetime.now(tz=UTC)
        input_run = models.Run(
            id="run-1",
            name="Test Run",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        expected_run = models.Run(
            id="run-1",
            name="Test Run",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        mock_repository.create_run.return_value = expected_run

        result = await run_service.setup_run(input_run)

        assert result == expected_run
        mock_repository.create_run.assert_called_once_with(input_run)

    @pytest.mark.asyncio
    async def test_setup_run_logs_created_run(
        self,
        run_service: service.RunService,
        mock_repository: AsyncMock,
        mocker: MockerFixture,
    ) -> None:
        """Test that setup_run logs when a run is created."""
        now = datetime.now(tz=UTC)
        test_run = models.Run(
            id="run-2",
            name="Logging Test",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )
        mock_repository.create_run.return_value = test_run

        mock_logger = mocker.patch("app.run.service.logger")

        await run_service.setup_run(test_run)

        mock_logger.info.assert_called_once_with("Created run %s", "run-2")
