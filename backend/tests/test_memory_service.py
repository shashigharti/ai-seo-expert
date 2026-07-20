from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.postgres.repositories.memory_repository import PostgresMemoryRepository
from app.application.memory.service import MemoryService
from app.domain.enums.memory_category import MemoryCategory
from app.domain.models.agent_result import Finding
from app.domain.models.memory_entry import MemoryEntry

REPO_URL = "https://github.com/example/project"


def _finding(title: str = "robots.txt blocks /products") -> Finding:
    return Finding(
        category="crawlability",
        severity="high",
        title=title,
        description="desc",
        evidence="robots.txt line 3",
        recommendation="fix it",
    )


async def test_record_false_positive_persists_a_memory_entry(db_session: AsyncSession):
    service = MemoryService(PostgresMemoryRepository(db_session))

    entry = await service.record_false_positive(REPO_URL, _finding(), rationale="Evidence didn't hold up")

    assert entry.category == MemoryCategory.FALSE_POSITIVE
    assert "robots.txt blocks /products" in entry.content
    assert "Evidence didn't hold up" in entry.content
    assert entry.expires_at is not None  # false positives have a finite TTL


async def test_record_approved_decision_persists_one_entry_per_finding(db_session: AsyncSession):
    service = MemoryService(PostgresMemoryRepository(db_session))

    entries = await service.record_approved_decision(
        REPO_URL, [_finding("issue A"), _finding("issue B")], pr_strategy="by_category"
    )

    assert len(entries) == 2
    assert all(e.category == MemoryCategory.APPROVED_DECISION for e in entries)


async def test_get_context_for_planning_returns_empty_string_when_no_memory(db_session: AsyncSession):
    service = MemoryService(PostgresMemoryRepository(db_session))
    assert await service.get_context_for_planning(REPO_URL) == ""


async def test_get_context_for_planning_includes_recorded_entries(db_session: AsyncSession):
    service = MemoryService(PostgresMemoryRepository(db_session))
    await service.record_false_positive(REPO_URL, _finding(), rationale="False alarm")

    context = await service.get_context_for_planning(REPO_URL)

    assert "false_positive" in context
    assert "False alarm" in context


async def test_get_context_for_planning_excludes_expired_entries(db_session: AsyncSession):
    repository = PostgresMemoryRepository(db_session)
    service = MemoryService(repository)
    expired_entry = MemoryEntry(
        id=__import__("uuid").uuid4(),
        repository_url=REPO_URL,
        category=MemoryCategory.FALSE_POSITIVE,
        content="This should not appear",
        created_at=datetime.now(timezone.utc) - timedelta(days=200),
        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    await repository.add(expired_entry)

    context = await service.get_context_for_planning(REPO_URL)

    assert context == ""


async def test_get_context_for_planning_is_scoped_to_the_repository(db_session: AsyncSession):
    service = MemoryService(PostgresMemoryRepository(db_session))
    await service.record_false_positive(REPO_URL, _finding(), rationale="For this repo only")

    context = await service.get_context_for_planning("https://github.com/example/other-repo")

    assert context == ""


async def test_delete_expired_removes_only_expired_rows(db_session: AsyncSession):
    repository = PostgresMemoryRepository(db_session)
    now = datetime.now(timezone.utc)
    await repository.add(
        MemoryEntry(
            id=__import__("uuid").uuid4(),
            repository_url=REPO_URL,
            category=MemoryCategory.FALSE_POSITIVE,
            content="expired",
            created_at=now - timedelta(days=200),
            expires_at=now - timedelta(days=1),
        )
    )
    await repository.add(
        MemoryEntry(
            id=__import__("uuid").uuid4(),
            repository_url=REPO_URL,
            category=MemoryCategory.CONVENTION,
            content="never expires",
            created_at=now,
            expires_at=None,
        )
    )

    deleted_count = await repository.delete_expired()

    assert deleted_count == 1
    remaining = await repository.list_for_repository(REPO_URL)
    assert len(remaining) == 1
    assert remaining[0].content == "never expires"
