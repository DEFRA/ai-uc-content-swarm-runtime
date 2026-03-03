import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging import getLogger

import uvicorn
from fastapi import FastAPI

import app.common.mongo as mongo
import app.common.tracing as tracing
import app.config as app_config
import app.health.router as health_router
import app.swarm.router as swarm_router

config = app_config.get_config()


logger = getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    # Startup
    client = await mongo.get_mongo_client()
    logger.info("MongoDB client connected")
    yield
    # Shutdown
    if client:
        await client.close()
        logger.info("MongoDB client closed")


app = FastAPI(lifespan=lifespan)

app.add_middleware(tracing.TraceIdMiddleware)

app.include_router(health_router.router)
app.include_router(swarm_router.router)


def main() -> None:  # pragma: no cover
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
