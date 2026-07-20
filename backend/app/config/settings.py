from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AISeo Expert"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://aiseo:aiseo@localhost:5432/aiseo"

    # CORS - never wildcard past local dev (Agents.md Security & Quality)
    allowed_origins: list[str] = ["http://localhost:5173"]
    allowed_methods: list[str] = ["GET", "POST", "PATCH", "DELETE", "OPTIONS"]
    allowed_headers: list[str] = ["Authorization", "Content-Type"]
    allow_credentials: bool = True

    # Auth (Phase 10)
    secret_key: str = "change-me-in-.env"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Qwen Cloud (Phase 3+) - OpenAI-compatible endpoint
    qwen_api_key: str | None = None
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    # Which real Qwen model backs each model_policies tier in
    # app/config/agents.yaml (docs/agent-architecture.md §6) - "basic" for
    # policies with thinking: false, "reasoning" for thinking: true.
    # Overridable per-deployment without editing the checked-in YAML (e.g.
    # to swap models if one runs out of quota - see backend/app/agents/
    # bootstrap.py's build_agent_factory).
    qwen_model_basic: str = "qwen-plus"
    qwen_model_reasoning: str = "qwen-max"

    # GitHub (Phase 8) - personal access token for the hackathon-scoped flow
    github_token: str | None = None

    # Artifact storage (Phase 10)
    artifact_store_backend: str = "local"  # "local" | "oss"
    artifact_store_local_path: str = "./data/artifacts"
    oss_bucket: str | None = None
    oss_endpoint: str | None = None
    oss_access_key_id: str | None = None
    oss_access_key_secret: str | None = None

    # Rate limiting (Phase 10)
    rate_limit_per_minute: int = 60


settings = Settings()
