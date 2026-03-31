from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from app.entrypoints import fastapi

client = TestClient(fastapi.app)


def test_lifespan(mocker: MockerFixture) -> None:
    mock_mongo_client = mocker.AsyncMock()
    mock_get_mongo = mocker.patch(
        "app.common.mongo.get_mongo_client", return_value=mock_mongo_client
    )

    mocker.patch("app.common.mongo.get_db", return_value=mocker.AsyncMock())
    mocker.patch("app.run.dependencies.get_run_repository")
    mocker.patch("app.run.dependencies.get_sqs_client")
    mocker.patch("app.run.dependencies.get_sqs_adapter")
    mocker.patch("app.run.dependencies.get_run_service")

    mock_listener = mocker.AsyncMock()
    mocker.patch("app.swarm.dependencies.get_sqs_listener", return_value=mock_listener)

    # Using TestClient as a context manager triggers lifespan startup/shutdown
    with TestClient(fastapi.app):
        mock_get_mongo.assert_called_once()  # Startup: connect called

    mock_mongo_client.close.assert_awaited_once()  # Shutdown: close called
    mock_listener.stop.assert_awaited_once()  # Shutdown: listener stop called


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 404
