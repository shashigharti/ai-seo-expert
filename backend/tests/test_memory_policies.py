import uuid
from datetime import datetime, timedelta, timezone

from app.domain.enums.memory_category import MemoryCategory
from app.domain.models.memory_entry import MemoryEntry
from app.domain.policies.memory_expiration_policy import expiry_for, is_expired
from app.domain.policies.memory_retrieval_policy import select_relevant_memory


def test_durable_categories_never_expire():
    now = datetime.now(timezone.utc)
    for category in (
        MemoryCategory.CONVENTION,
        MemoryCategory.USER_PREFERENCE,
        MemoryCategory.IGNORED_PATH,
        MemoryCategory.FRAMEWORK_INFO,
    ):
        assert expiry_for(category, now) is None


def test_approved_decision_and_false_positive_have_finite_ttl():
    now = datetime.now(timezone.utc)
    assert expiry_for(MemoryCategory.APPROVED_DECISION, now) == now + timedelta(days=180)
    assert expiry_for(MemoryCategory.FALSE_POSITIVE, now) == now + timedelta(days=90)


def test_is_expired_true_after_expiry_time():
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=1)
    assert is_expired(past, now=now) is True


def test_is_expired_false_before_expiry_time():
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    assert is_expired(future, now=now) is False


def test_is_expired_false_when_no_expiry_set():
    assert is_expired(None) is False


def _entry(category: MemoryCategory, created_at: datetime, expires_at=None) -> MemoryEntry:
    return MemoryEntry(
        id=uuid.uuid4(),
        repository_url="https://github.com/example/project",
        category=category,
        content="some content",
        created_at=created_at,
        expires_at=expires_at,
    )


def test_select_relevant_memory_filters_out_expired_entries():
    now = datetime.now(timezone.utc)
    live = _entry(MemoryCategory.FALSE_POSITIVE, now, expires_at=now + timedelta(days=1))
    expired = _entry(MemoryCategory.FALSE_POSITIVE, now, expires_at=now - timedelta(days=1))

    selected = select_relevant_memory([live, expired], now=now)

    assert selected == [live]


def test_select_relevant_memory_caps_entries_per_category():
    now = datetime.now(timezone.utc)
    entries = [
        _entry(MemoryCategory.FALSE_POSITIVE, now - timedelta(minutes=i))
        for i in range(5)
    ]

    selected = select_relevant_memory(entries, max_per_category=2, now=now)

    assert len(selected) == 2
    # Keeps the most recent ones (smallest offset = most recent)
    assert selected[0].created_at >= selected[1].created_at


def test_select_relevant_memory_caps_independently_per_category():
    now = datetime.now(timezone.utc)
    false_positives = [_entry(MemoryCategory.FALSE_POSITIVE, now) for _ in range(3)]
    conventions = [_entry(MemoryCategory.CONVENTION, now) for _ in range(3)]

    selected = select_relevant_memory(false_positives + conventions, max_per_category=2, now=now)

    assert len(selected) == 4
