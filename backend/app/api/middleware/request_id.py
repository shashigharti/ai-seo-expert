import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config.logging import request_id_var

# "Basic tracing hooks" (Phase 10): a per-request correlation id, propagated
# into log records via the contextvar in app/config/logging.py and echoed
# back as a response header. Not a full distributed-tracing setup (no span/
# trace hierarchy, no exporter) - that's a bigger addition than this
# project's stack currently calls for; this is the minimal real version of
# "tracing" that makes "find every log line for this one request" possible.


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response
