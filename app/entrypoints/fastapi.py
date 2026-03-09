import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import fastapi
import uvicorn

import app.common.mongo as mongo
import app.common.tracing as tracing
import app.config as app_config
import app.health.router as health_router
import app.run.context.router as context_router
import app.run.router as run_router
import app.swarm.router as swarm_router

config = app_config.get_config()


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: fastapi.FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    client = await mongo.get_mongo_client()
    logger.info("MongoDB client connected")
    yield
    # Shutdown
    if client:
        await client.close()
        logger.info("MongoDB client closed")


app = fastapi.FastAPI(lifespan=lifespan)

app.add_middleware(tracing.TraceIdMiddleware)

app.include_router(health_router.router)
app.include_router(swarm_router.router)
app.include_router(context_router.router)
app.include_router(run_router.router)


@app.exception_handler(fastapi.exceptions.RequestValidationError)
async def validation_exception_handler(
    _: fastapi.Request,
    exc: fastapi.exceptions.RequestValidationError,
) -> fastapi.responses.JSONResponse:
    """Convert validation errors to 400 Bad Request instead of 422."""
    print(
        f"Validation error: {exc.errors()}"
    )  # Log the validation errors for debugging
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
