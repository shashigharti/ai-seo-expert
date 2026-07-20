import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgres.database import Base
from app.domain.enums.workflow_status import WorkflowStatus


class WorkflowModel(Base):
    __tablename__ = "workflows"

    # sqlalchemy.Uuid is dialect-agnostic: native UUID on Postgres, CHAR(32) on
    # SQLite - lets the same model back both the real DB and the in-memory
    # SQLite test database from the fastapi-patterns testing pattern.
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_url: Mapped[str] = mapped_column(String(500))
    branch: Mapped[str] = mapped_column(String(255), default="master")
    goal: Mapped[str] = mapped_column(String(2000))
    status: Mapped[str] = mapped_column(String(30), default=WorkflowStatus.PENDING.value)
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
