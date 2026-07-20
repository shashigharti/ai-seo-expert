from app.api.middleware.rate_limiter import InMemoryRateLimiter


def test_allows_requests_up_to_the_limit():
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60.0)
    now = 1000.0

    assert limiter.is_allowed("client-a", now=now) is True
    assert limiter.is_allowed("client-a", now=now) is True
    assert limiter.is_allowed("client-a", now=now) is True


def test_rejects_requests_over_the_limit_within_the_window():
    limiter = InMemoryRateLimiter(max_requests=2, window_seconds=60.0)
    now = 1000.0

    assert limiter.is_allowed("client-a", now=now) is True
    assert limiter.is_allowed("client-a", now=now) is True
    assert limiter.is_allowed("client-a", now=now) is False


def test_allows_again_once_the_window_slides_past_old_hits():
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60.0)

    assert limiter.is_allowed("client-a", now=1000.0) is True
    assert limiter.is_allowed("client-a", now=1010.0) is False
    assert limiter.is_allowed("client-a", now=1061.0) is True  # 61s later, window cleared


def test_tracks_each_client_independently():
    limiter = InMemoryRateLimiter(max_requests=1, window_seconds=60.0)
    now = 1000.0

    assert limiter.is_allowed("client-a", now=now) is True
    assert limiter.is_allowed("client-b", now=now) is True
    assert limiter.is_allowed("client-a", now=now) is False
    assert limiter.is_allowed("client-b", now=now) is False
