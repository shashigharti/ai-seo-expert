"""Unit tests for the ExternalServiceError catch-all handler in isolation.

No current route lets an ExternalServiceError escape uncaught (PR
generation's own try/except now covers every external call it makes) - this
handler exists as a fallback for any future route that doesn't, or forgets
to. Testing it against a throwaway route, rather than trying to force a real
route into this state, is the honest way to verify it without fabricating a
business scenario that doesn't actually occur today.
"""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.error_handlers import register_error_handlers
from app.domain.errors import ExternalErrorKind, ExternalServiceError


def _build_app() -> FastAPI:
    app = FastAPI()
    register_error_handlers(app)

    @app.get("/raise/{kind}")
    async def raise_error(kind: str):
        error_kind = ExternalErrorKind(kind)
        raise ExternalServiceError(service="Qwen Cloud", kind=error_kind, message=f"curated {kind} message")

    return app


async def test_auth_kind_returns_502_with_curated_message():
    async with AsyncClient(transport=ASGITransport(app=_build_app()), base_url="http://test") as client:
        response = await client.get("/raise/auth")

    assert response.status_code == 502
    assert response.json() == {"error": {"code": "QWEN_CLOUD_AUTH", "message": "curated auth message"}}


async def test_rate_limit_kind_returns_503():
    async with AsyncClient(transport=ASGITransport(app=_build_app()), base_url="http://test") as client:
        response = await client.get("/raise/rate_limit")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "QWEN_CLOUD_RATE_LIMIT"


async def test_network_kind_returns_502():
    async with AsyncClient(transport=ASGITransport(app=_build_app()), base_url="http://test") as client:
        response = await client.get("/raise/network")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "QWEN_CLOUD_NETWORK"
