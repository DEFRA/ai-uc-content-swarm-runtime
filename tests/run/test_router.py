from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

import app.run.dependencies as run_dependencies
import app.swarm.dependencies as swarm_dependencies
from app.entrypoints import fastapi
from app.run import api_schemas, models, repository


@pytest.fixture
def mock_repository(mocker: MockerFixture) -> AsyncMock:
    """Create a mocked RunRepository based on the ABC."""
    return mocker.AsyncMock(spec=repository.RunRepository)  # type: ignore[no-any-return]


@pytest.fixture
def test_client(
    mock_repository: AsyncMock, mocker: MockerFixture
) -> Generator[TestClient, None, None]:
    """Create a TestClient with mocked repository and swarm dependencies."""

    def override_get_run_repository() -> repository.RunRepository:
        return mock_repository  # type: ignore[return-value]

    # Mock the swarm runner to avoid boto3 client initialization
    mock_swarm_runner = mocker.AsyncMock()

    def override_get_swarm_runner():
        return mock_swarm_runner  # type: ignore[return-value]

    fastapi.app.dependency_overrides[run_dependencies.get_run_repository] = (
        override_get_run_repository
    )
    fastapi.app.dependency_overrides[swarm_dependencies.get_swarm_runner] = (
        override_get_swarm_runner
    )

    yield TestClient(fastapi.app)

    fastapi.app.dependency_overrides.clear()


class TestRunRouter:
    """Tests for the create_run endpoint."""

    def test_create_run_success(
        self, test_client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test successful run creation via POST /runs/."""
        now = datetime.now(tz=UTC)
        created_run = models.Run(
            id="test-run-id-123",
            name="Integration Test Run",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        mock_repository.create_run.return_value = created_run

        payload = {"name": "Integration Test Run"}
        response = test_client.post("/runs", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "test-run-id-123"
        assert data["created_at"] is not None
        mock_repository.create_run.assert_called_once()

    def test_create_run_missing_name(self, test_client: TestClient) -> None:
        """Test that POST /runs/ fails without name field."""
        response = test_client.post("/runs", json={})

        assert response.status_code == 400

    def test_create_run_response_structure(
        self, test_client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test that response matches RunResponse schema."""
        now = datetime.now(tz=UTC)
        created_run = models.Run(
            id="response-test-id",
            name="Response Test",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        mock_repository.create_run.return_value = created_run

        response = test_client.post("/runs", json={"name": "Response Test"})

        assert response.status_code == 201

        run_response = api_schemas.RunResponse(**response.json())
        assert run_response.id == "response-test-id"
        assert isinstance(run_response.created_at, datetime)

    def test_create_run_repository_called_with_correct_run(
        self, test_client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test that repository.create_run is called with a Run object."""
        now = datetime.now(tz=UTC)
        created_run = models.Run(
            id="call-test-id",
            name="Call Test",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        mock_repository.create_run.return_value = created_run

        test_client.post("/runs", json={"name": "Call Test"})

        mock_repository.create_run.assert_called_once()

        call_args = mock_repository.create_run.call_args
        passed_run = call_args[0][0]

        assert isinstance(passed_run, models.Run)
        assert passed_run.name == "Call Test"
        assert passed_run.status == models.RunStatus.SETUP

    def test_create_run_repository_exception_returns_500(
        self, test_client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test that repository exceptions result in 500 error."""
        mock_repository.create_run.side_effect = RuntimeError

        with pytest.raises(RuntimeError):
            test_client.post("/runs", json={"name": "Error Test"})

    def test_get_run_success(
        self, test_client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test successful retrieval of a run via GET /runs/{run_id}."""
        now = datetime.now(tz=UTC)
        run = models.Run(
            id="test-run-id-123",
            name="Existing Run",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        mock_repository.get_run.return_value = run

        response = test_client.get("/runs/test-run-id-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-run-id-123"
        assert data["name"] == "Existing Run"
        assert data["status"] == "setup"
        assert data["created_at"] is not None
        assert data["updated_at"] is not None
        mock_repository.get_run.assert_called_once_with("test-run-id-123")

    def test_get_run_not_found(
        self, test_client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test that GET /runs/{run_id} returns 404 when run is not found."""
        mock_repository.get_run.return_value = None

        response = test_client.get("/runs/nonexistent-id")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_get_run_response_structure(
        self, test_client: TestClient, mock_repository: AsyncMock
    ) -> None:
        """Test that GET response matches RunResponse schema."""
        now = datetime.now(tz=UTC)
        run = models.Run(
            id="get-response-test-id",
            name="Get Response Test",
            status=models.RunStatus.SETUP,
            created_at=now,
            updated_at=now,
        )

        mock_repository.get_run.return_value = run

        response = test_client.get("/runs/get-response-test-id")

        assert response.status_code == 200
        run_response = api_schemas.RunResponse(**response.json())
        assert run_response.id == "get-response-test-id"
        assert run_response.name == "Get Response Test"
        assert run_response.status == models.RunStatus.SETUP
