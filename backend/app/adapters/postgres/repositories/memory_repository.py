from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.models.memory_entry import MemoryEntryModel
from app.domain.models.memory_entry import MemoryEntry


class PostgresMemoryRepository:
    """Adapter implementing the MemoryRepository port via SQLAlchemy."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add(self, entry: MemoryEntry) -> MemoryEntry:
        row = MemoryEntryModel(
            id=entry.id,
            repository_url=entry.repository_url,
            category=entry.category.value,
            content=entry.content,
            expires_at=entry.expires_at,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return MemoryEntry.model_validate(row)

    async def list_for_repository(self, repository_url: str) -> list[MemoryEntry]:
        result = await self.db.execute(
            select(MemoryEntryModel)
            .where(MemoryEntryModel.repository_url == repository_url)
            .order_by(MemoryEntryModel.created_at.desc())
        )
        return [MemoryEntry.model_validate(row) for row in result.scalars()]

    async def delete_expired(self) -> int:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            delete(MemoryEntryModel)
            .where(MemoryEntryModel.expires_at.is_not(None))
            .where(MemoryEntryModel.expires_at <= now)
        )
        await self.db.commit()
        return result.rowcount or 0
