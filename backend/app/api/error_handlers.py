from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.domain.errors import ExternalErrorKind, ExternalServiceError

# RATE_LIMIT gets 503 (temporarily unavailable, retry later); everything
# else gets 502 (our server's upstream dependency failed) - never a 4xx,
# since it's not the caller's own request that was invalid.
_STATUS_CODE_BY_KIND = {
    ExternalErrorKind.RATE_LIMIT: 503,
}
_DEFAULT_EXTERNAL_ERROR_STATUS_CODE = 502


def register_error_handlers(app: FastAPI) -> None:
    """Normalize error responses into docs/api-contracts.md's envelope:

    {"error": {"code": "...", "message": "..."}}
    """

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict) and "code" in detail and "message" in detail:
            body = {"error": detail}
        else:
            body = {"error": {"code": "HTTP_ERROR", "message": str(detail)}}
        return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)

    @app.exception_handler(ExternalServiceError)
    async def handle_external_service_error(request: Request, exc: ExternalServiceError) -> JSONResponse:
        """Fallback for a classified GitHub/Qwen Cloud failure that escapes
        a route with no more specific handling of its own - every current
        route that calls an external service synchronously (PR generation)
        already catches these itself and records a per-result error instead
        of raising, so this exists for any future route that doesn't, or
        forgets to. Without it, such a failure would fall through to
        Starlette's generic 500, which doesn't match this app's own error
        envelope and gives the frontend nothing but "Request failed with
        status 500".
        """
        status_code = _STATUS_CODE_BY_KIND.get(exc.kind, _DEFAULT_EXTERNAL_ERROR_STATUS_CODE)
        code = f"{exc.service.upper().replace(' ', '_')}_{exc.kind.value.upper()}"
        return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": exc.message}})
