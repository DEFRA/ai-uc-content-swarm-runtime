import logging

import httpx

from app import config
import app.common.tracing as tracing

config = config.get_config()

logger = logging.getLogger(__name__)


async def async_hook_request_tracing(request):
    trace_id = tracing.ctx_trace_id.get(None)
    if trace_id:
        request.headers[config.tracing_header] = trace_id


def hook_request_tracing(request):
    trace_id = tracing.ctx_trace_id.get(None)
    if trace_id:
        request.headers[config.tracing_header] = trace_id


def create_async_client(request_timeout: int = 30) -> httpx.AsyncClient:
    """
    Create an async HTTP client with configurable timeout.

    Args:
        request_timeout: Request timeout in seconds

    Returns:
        Configured httpx.AsyncClient instance
    """
    client_kwargs = {
        "timeout": request_timeout,
        "event_hooks": {"request": [async_hook_request_tracing]},
    }

    return httpx.AsyncClient(**client_kwargs)


def create_client(request_timeout: int = 30) -> httpx.Client:
    """
    Create a sync HTTP client with configurable timeout.

    Args:
        request_timeout: Request timeout in seconds

    Returns:
        Configured httpx.Client instance
    """
    client_kwargs = {
        "timeout": request_timeout,
        "event_hooks": {"request": [hook_request_tracing]},
    }

    return httpx.Client(**client_kwargs)
