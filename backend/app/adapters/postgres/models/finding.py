import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.adapters.postgres.database import Base
from app.domain.enums.finding_status import FindingStatus


class FindingModel(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("workflows.id"))
    task_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("tasks.id"))
    agent_name: Mapped[str] = mapped_column(String(100))
    finding: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default=FindingStatus.PENDING.value)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
