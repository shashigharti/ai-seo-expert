import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgres.database import Base


class PullRequestModel(Base):
    __tablename__ = "pull_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("workflows.id"))
    status: Mapped[str] = mapped_column(String(20))
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    repository_url: Mapped[str] = mapped_column(String(500))
    branch_name: Mapped[str] = mapped_column(String(200))
    commit_summary: Mapped[str] = mapped_column(String(500))
    finding_ids: Mapped[list] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
