import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import fastapi
import uvicorn

from app import config as app_config
from app.common import mongo, tracing
from app.health import router as health_router
from app.run import dependencies as run_dependencies
from app.run import router as run_router
from app.swarm import dependencies as swarm_dependencies
from app.swarm import router as swarm_router
from app.swarm import sqs

config = app_config.get_config()


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: fastapi.FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    client = await mongo.get_mongo_client()
    logger.info("MongoDB client connected")

    db = await mongo.get_db(client)

    run_repository = run_dependencies.get_run_repository(db)
    sqs_client = run_dependencies.get_sqs_client()
    sqs_adapter = run_dependencies.get_sqs_adapter(sqs_client)
    run_service = run_dependencies.get_run_service(run_repository, sqs_adapter)

    sqs_listener: sqs.AbstractQueueListener = swarm_dependencies.get_sqs_listener(
        run_result_handler=run_service
    )

    listener_task = asyncio.create_task(sqs_listener.start())
    logger.info("SQS listener started")

    yield

    # Shutdown
    if sqs_listener:
        await sqs_listener.stop()
        logger.info("SQS listener stopped")

    if listener_task:
        listener_task.cancel()

        await listener_task

    if client:
        await client.close()
        logger.info("MongoDB client closed")


app = fastapi.FastAPI(lifespan=lifespan)

app.add_middleware(tracing.TraceIdMiddleware)

app.include_router(health_router.router)
app.include_router(swarm_router.router)
app.include_router(run_router.router)


@app.exception_handler(fastapi.exceptions.RequestValidationError)
async def validation_exception_handler(
    _: fastapi.Request,
    exc: fastapi.exceptions.RequestValidationError,
) -> fastapi.responses.JSONResponse:
    """Convert validation errors to 400 Bad Request instead of 422."""
    return fastapi.responses.JSONResponse(
        status_code=fastapi.status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.errors()},
    )


def main() -> None:  # pragma: no cover
    if config.http_proxy:
        os.environ["HTTP_PROXY"] = str(config.http_proxy)
        os.environ["HTTPS_PROXY"] = str(config.http_proxy)

    uvicorn.run(
        "app.entrypoints.fastapi:app",
        host=config.host,
        port=config.port,
        log_config=config.log_config,
        reload=config.python_env == "development",
    )


if __name__ == "__main__":  # pragma: no cover
    main()
