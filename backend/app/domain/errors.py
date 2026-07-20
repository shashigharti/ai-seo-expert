from enum import Enum


class ExternalErrorKind(str, Enum):
    """A small, user-meaningful classification for failures calling an
    external service (GitHub, Qwen Cloud) - auth/not-found/rate-limit/
    network are distinguishable causes a user can actually act on; UNKNOWN
    is the honest fallback for anything else, never raw exception text.
    """

    AUTH = "auth"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    NETWORK = "network"
    UNKNOWN = "unknown"


class ExternalServiceError(Exception):
    """Raised by adapters (GitHub, Qwen Cloud) when a call to an external
    service fails. `message` is always a curated, user-safe description -
    never a stringified raw exception - so it's safe to surface directly in
    an API response or the UI.
    """

    def __init__(self, service: str, kind: ExternalErrorKind, message: str) -> None:
        super().__init__(message)
        self.service = service
        self.kind = kind
        self.message = message


_GENERIC_FALLBACK_MESSAGE = "An unexpected error occurred. Check server logs for details."


def user_facing_message(exc: Exception) -> str:
    """The one place that decides what an exception is allowed to show a
    user: `exc.message` for a classified `ExternalServiceError` (already
    curated, safe to display), otherwise a fixed generic fallback - never
    `str(exc)`, which could be anything (per this project's OWASP stance
    against leaking internal implementation details).
    """
    if isinstance(exc, ExternalServiceError):
        return exc.message
    return _GENERIC_FALLBACK_MESSAGE
