from datetime import datetime, timedelta, timezone

from app.domain.enums.memory_category import MemoryCategory

# docs/agent-architecture.md §12 doesn't prescribe TTLs, so these are a
# reasoned default: durable facts (conventions, preferences, false
# positives - things that stay true until someone says otherwise) never
# expire; point-in-time facts (a specific approved decision) age out so
# memory doesn't grow into an ever-accumulating, increasingly stale pile.
_TTL_DAYS: dict[MemoryCategory, int | None] = {
    MemoryCategory.CONVENTION: None,
    MemoryCategory.APPROVED_DECISION: 180,
    MemoryCategory.USER_PREFERENCE: None,
    MemoryCategory.IGNORED_PATH: None,
    MemoryCategory.FRAMEWORK_INFO: None,
    MemoryCategory.FALSE_POSITIVE: 90,
}


def expiry_for(category: MemoryCategory, created_at: datetime) -> datetime | None:
    ttl_days = _TTL_DAYS[category]
    if ttl_days is None:
        return None
    return created_at + timedelta(days=ttl_days)


def is_expired(expires_at: datetime | None, now: datetime | None = None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        # SQLite (used in tests) doesn't preserve timezone-awareness across
        # a round-trip even on a DateTime(timezone=True) column, unlike real
        # Postgres - every datetime this app produces is UTC
        # (datetime.now(timezone.utc)), so a naive value read back is
        # assumed UTC rather than raising on the comparison below.
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) >= expires_at
