from enum import Enum


class MemoryCategory(str, Enum):
    """docs/agent-architecture.md §12 - what memory should store."""

    CONVENTION = "convention"
    APPROVED_DECISION = "approved_decision"
    USER_PREFERENCE = "user_preference"
    IGNORED_PATH = "ignored_path"
    FRAMEWORK_INFO = "framework_info"
    FALSE_POSITIVE = "false_positive"
