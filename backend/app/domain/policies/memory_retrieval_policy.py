from datetime import datetime, timezone

from app.domain.models.memory_entry import MemoryEntry
from app.domain.policies.memory_expiration_policy import is_expired

DEFAULT_MAX_ENTRIES_PER_CATEGORY = 10


def select_relevant_memory(
    entries: list[MemoryEntry],
    max_per_category: int = DEFAULT_MAX_ENTRIES_PER_CATEGORY,
    now: datetime | None = None,
) -> list[MemoryEntry]:
    """Filters out expired entries and caps how many of each category get
    used as context - repository-architecture.md §12 doesn't specify a
    limit, but an unbounded memory dump defeats the purpose (it's meant to
    inform a prompt, not replace one) and risks drowning out the current
    workflow's actual task in stale context.

    Keeps the most recent entries per category when capping.
    """
    now = now or datetime.now(timezone.utc)
    live = [e for e in entries if not is_expired(e.expires_at, now)]
    live.sort(key=lambda e: e.created_at, reverse=True)

    counts: dict[str, int] = {}
    selected: list[MemoryEntry] = []
    for entry in live:
        count = counts.get(entry.category.value, 0)
        if count >= max_per_category:
            continue
        counts[entry.category.value] = count + 1
        selected.append(entry)
    return selected
