import httpx
import pytest

from app.domain.errors import ExternalErrorKind, ExternalServiceError
from app.tools.github_file_reader import (
    InvalidRepositoryUrlError,
    list_repository_files,
    parse_owner_repo,
    read_repository_file,
)


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://github.com/example/project", ("example", "project")),
        ("https://github.com/example/project/", ("example", "project")),
        ("https://github.com/example/project.git", ("example", "project")),
    ],
)
def test_parse_owner_repo(url, expected):
    assert parse_owner_repo(url) == expected


def test_parse_owner_repo_rejects_non_github_url():
    with pytest.raises(InvalidRepositoryUrlError):
        parse_owner_repo("https://gitlab.com/example/project")


async def test_read_repository_file_returns_content_on_200(monkeypatch):
    async def fake_get(self, url, **kwargs):
        assert url == "https://raw.githubusercontent.com/example/project/main/robots.txt"
        return httpx.Response(200, text="User-agent: *\nDisallow:", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    content = await read_repository_file("https://github.com/example/project", "robots.txt", ref="main")
    assert content == "User-agent: *\nDisallow:"


async def test_read_repository_file_returns_none_on_404(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(404)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    content = await read_repository_file("https://github.com/example/project", "missing.txt")
    assert content is None


async def test_read_repository_file_raises_curated_error_on_server_error(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(500, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ExternalServiceError) as exc_info:
        await read_repository_file("https://github.com/example/project", "robots.txt")
    assert exc_info.value.kind == ExternalErrorKind.UNKNOWN
    assert "500" not in exc_info.value.message


async def test_read_repository_file_raises_rate_limit_on_429(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(429, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ExternalServiceError) as exc_info:
        await read_repository_file("https://github.com/example/project", "robots.txt")
    assert exc_info.value.kind == ExternalErrorKind.RATE_LIMIT


async def test_read_repository_file_raises_auth_on_401(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(401, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ExternalServiceError) as exc_info:
        await read_repository_file("https://github.com/example/project", "robots.txt")
    assert exc_info.value.kind == ExternalErrorKind.AUTH


async def test_read_repository_file_raises_network_on_connection_error(monkeypatch):
    async def fake_get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ExternalServiceError) as exc_info:
        await read_repository_file("https://github.com/example/project", "robots.txt")
    assert exc_info.value.kind == ExternalErrorKind.NETWORK


async def test_list_repository_files_returns_blob_paths_only(monkeypatch):
    tree = {
        "tree": [
            {"path": "index.html", "type": "blob"},
            {"path": "src", "type": "tree"},
            {"path": "src/App.jsx", "type": "blob"},
            {"path": "node_modules/react/index.js", "type": "blob"},
            {"path": ".git/HEAD", "type": "blob"},
        ],
        "truncated": False,
    }

    async def fake_get(self, url, **kwargs):
        assert url == "https://api.github.com/repos/example/project/git/trees/main"
        assert kwargs["params"] == {"recursive": "1"}
        assert kwargs["headers"]["User-Agent"]
        return httpx.Response(200, json=tree, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    files = await list_repository_files("https://github.com/example/project", ref="main")

    # blobs only (no "src" tree entry), and node_modules/.git excluded
    assert files == ["index.html", "src/App.jsx"]


async def test_list_repository_files_caps_result_length(monkeypatch):
    tree = {"tree": [{"path": f"file{i}.html", "type": "blob"} for i in range(500)], "truncated": False}

    async def fake_get(self, url, **kwargs):
        return httpx.Response(200, json=tree, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    files = await list_repository_files("https://github.com/example/project")

    assert len(files) == 300


async def test_list_repository_files_raises_not_found_on_404(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ExternalServiceError) as exc_info:
        await list_repository_files("https://github.com/example/project", ref="no-such-branch")
    assert exc_info.value.kind == ExternalErrorKind.NOT_FOUND


async def test_list_repository_files_raises_rate_limit_on_429(monkeypatch):
    async def fake_get(self, url, **kwargs):
        return httpx.Response(429, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ExternalServiceError) as exc_info:
        await list_repository_files("https://github.com/example/project")
    assert exc_info.value.kind == ExternalErrorKind.RATE_LIMIT


async def test_list_repository_files_raises_network_on_connection_error(monkeypatch):
    async def fake_get(self, url, **kwargs):
        raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    with pytest.raises(ExternalServiceError) as exc_info:
        await list_repository_files("https://github.com/example/project")
    assert exc_info.value.kind == ExternalErrorKind.NETWORK
