import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class InMemoryRateLimiter:
    """Fixed-size sliding window, per-client-IP. In-process only - matches
    this project's single-process deployment model (no Redis/broker
    dependency exists anywhere else in this codebase either). A multi-
    instance deployment would need a shared store instead; noted as a
    known limitation, not silently pretended away.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str, now: float | None = None) -> bool:
        now = now if now is not None else time.monotonic()
        hits = self._hits[client_key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= self.max_requests:
            return False
        hits.append(now)
        return True


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: InMemoryRateLimiter) -> None:
        super().__init__(app)
        self._limiter = limiter

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        client_key = request.client.host if request.client else "unknown"
        if not self._limiter.is_allowed(client_key):
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "Too many requests"}},
            )
        return await call_next(request)
