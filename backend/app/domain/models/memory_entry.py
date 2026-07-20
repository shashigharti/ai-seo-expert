from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.domain.enums.memory_category import MemoryCategory


class MemoryEntry(BaseModel):
    """docs/agent-architecture.md §12: "Store concise decisions and
    evidence. Do not store raw chain-of-thought." `content` is a short,
    human-readable summary - never a prompt/reasoning dump.
    """

    id: UUID
    repository_url: str
    category: MemoryCategory
    content: str
    created_at: datetime
    expires_at: datetime | None = None

    model_config = {"from_attributes": True}
