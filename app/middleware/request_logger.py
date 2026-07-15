"""
HTTP Request Logger Middleware.

Automatically logs every request with:
- A unique request_id (also returned in the X-Request-ID response header)
- HTTP method, path, client IP
- Response status code + duration in ms
- Full exception traceback on unhandled errors

The request_id and client_ip are bound to the structlog context, so they
appear automatically in ALL log lines emitted during that request.
"""
import time
import uuid
import structlog
import structlog.contextvars
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())
        start_time = time.time()

        # Clear any leftovers from a previous request on this thread
        structlog.contextvars.clear_contextvars()

        # Bind context — these fields appear in every log line for this request
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        logger.info("request_started")

        try:
            response: Response = await call_next(request)
        except Exception as exc:
            logger.error(
                "request_unhandled_exception",
                exception_type=type(exc).__name__,
                exc_info=True,
            )
            raise

        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.info(
            "request_finished",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # Return the request ID to the client so they can reference it in support tickets
        response.headers["X-Request-ID"] = request_id
        return response
