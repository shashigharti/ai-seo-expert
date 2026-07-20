"""
Main entry point for the AISeo Expert FastAPI application. Configures the
app, sets up CORS middleware, registers error handlers, and includes routers
for workflow endpoints (docs/api-contracts.md).
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.adapters.postgres.database import Base, engine
from app.api.error_handlers import register_error_handlers
from app.api.middleware.rate_limiter import InMemoryRateLimiter, RateLimitMiddleware
from app.api.middleware.request_id import RequestIdMiddleware
from app.api.routes import auth, workflows
from app.config.logging import configure_logging, get_logger
from app.config.settings import settings

logger = get_logger(__name__)

# Populated by the Docker build (docker/backend.Dockerfile copies the
# frontend's `dist/` here) - per docs/frontend-architecture.md §2, FastAPI
# serves the built React app directly rather than running two services.
# Absent in local dev (`uvicorn` run straight from source, no frontend
# build step), so mounting is conditional.
STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(debug=settings.debug)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    # Dev/demo convenience: auto-create tables. Production schema changes go
    # through Alembic migrations (backend/alembic) - see docs/deployment.md.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # Middleware order: Starlette wraps outermost-added-last, so
    # RequestIdMiddleware wraps RateLimitMiddleware (every request,
    # including rate-limited ones, gets a request id in its logs) - and
    # CORSMiddleware is added last of all, making it the outermost layer of
    # the three. That's required, not stylistic: RateLimitMiddleware
    # short-circuits with its own 429 JSONResponse without ever calling
    # call_next(), so if CORS sat inside it, a rate-limited response would
    # skip CORS's response processing entirely and reach the browser with
    # no Access-Control-Allow-Origin header. A cross-origin fetch() to a
    # response like that doesn't surface the 429/its JSON body at all -
    # the browser blocks reading it and fetch() throws a generic network
    # error, which the frontend can't distinguish from "server unreachable"
    # (this is exactly what "Failed to load workflow" turned out to be).
    limiter = InMemoryRateLimiter(
        max_requests=settings.rate_limit_per_minute, window_seconds=60.0
    )
    app.add_middleware(RateLimitMiddleware, limiter=limiter)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=settings.allow_credentials,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )

    register_error_handlers(app)

    app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
    app.include_router(workflows.router, prefix="/api/workflows", tags=["Workflows"])

    if STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="frontend-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            # React Router client-side routing: any path FastAPI doesn't
            # already own (api/*, assets/*, docs) resolves to index.html and
            # the frontend router takes it from there.
            return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
