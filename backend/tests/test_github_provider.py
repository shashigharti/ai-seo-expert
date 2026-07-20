from unittest.mock import MagicMock, patch

import pytest
import requests
from github.GithubException import BadCredentialsException, RateLimitExceededException, UnknownObjectException

from app.adapters.github.provider import (
    GitHubClientConfigurationError,
    GitHubOperationError,
    GitHubProvider,
)
from app.domain.errors import ExternalErrorKind
from app.domain.models.patch import ProposedPatch


async def test_get_default_branch_raises_without_token():
    provider = GitHubProvider(token=None)
    with pytest.raises(GitHubClientConfigurationError):
        await provider.get_default_branch("https://github.com/example/project")


async def test_open_pull_request_raises_without_token():
    provider = GitHubProvider(token=None)
    with pytest.raises(GitHubClientConfigurationError):
        await provider.open_pull_request(
            "https://github.com/example/project", "main", "aiseo/fix-x", [], "title", "body"
        )


async def test_get_default_branch_returns_repo_default_branch():
    mock_repo = MagicMock(default_branch="main")
    mock_client = MagicMock()
    mock_client.get_repo.return_value = mock_repo

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="test-token")
        branch = await provider.get_default_branch("https://github.com/example/project")

    assert branch == "main"
    mock_client.get_repo.assert_called_once_with("example/project")


async def test_open_pull_request_creates_branch_updates_existing_file_and_opens_pr():
    mock_repo = MagicMock()
    mock_repo.get_branch.return_value.commit.sha = "base-sha-123"
    mock_repo.get_contents.return_value = MagicMock(sha="existing-file-sha")
    mock_repo.create_pull.return_value.html_url = "https://github.com/example/project/pull/1"

    mock_client = MagicMock()
    mock_client.get_repo.return_value = mock_repo

    patch_obj = ProposedPatch(file_path="robots.txt", new_content="new content", commit_message="fix robots.txt")

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="test-token")
        url = await provider.open_pull_request(
            repository_url="https://github.com/example/project",
            base_branch="main",
            new_branch="aiseo/fix-crawlability",
            patches=[patch_obj],
            pr_title="Fix crawlability issues",
            pr_body="body",
        )

    assert url == "https://github.com/example/project/pull/1"
    mock_repo.create_git_ref.assert_called_once_with(ref="refs/heads/aiseo/fix-crawlability", sha="base-sha-123")
    mock_repo.update_file.assert_called_once_with(
        path="robots.txt",
        message="fix robots.txt",
        content="new content",
        sha="existing-file-sha",
        branch="aiseo/fix-crawlability",
    )
    mock_repo.create_file.assert_not_called()
    mock_repo.create_pull.assert_called_once_with(
        base="main", head="aiseo/fix-crawlability", title="Fix crawlability issues", body="body"
    )


async def test_open_pull_request_creates_new_file_when_it_does_not_exist():
    mock_repo = MagicMock()
    mock_repo.get_branch.return_value.commit.sha = "base-sha-123"
    mock_repo.get_contents.side_effect = UnknownObjectException(404, "Not Found", None)
    mock_repo.create_pull.return_value.html_url = "https://github.com/example/project/pull/2"

    mock_client = MagicMock()
    mock_client.get_repo.return_value = mock_repo

    patch_obj = ProposedPatch(file_path="sitemap.xml", new_content="<urlset></urlset>", commit_message="add sitemap")

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="test-token")
        await provider.open_pull_request(
            "https://github.com/example/project", "main", "aiseo/fix-x", [patch_obj], "title", "body"
        )

    mock_repo.create_file.assert_called_once_with(
        path="sitemap.xml", message="add sitemap", content="<urlset></urlset>", branch="aiseo/fix-x"
    )
    mock_repo.update_file.assert_not_called()


async def test_open_pull_request_wraps_github_exceptions():
    from github.GithubException import GithubException

    mock_repo = MagicMock()
    mock_repo.get_branch.side_effect = GithubException(403, "Forbidden", None)
    mock_client = MagicMock()
    mock_client.get_repo.return_value = mock_repo

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="test-token")
        with pytest.raises(GitHubOperationError):
            await provider.open_pull_request(
                "https://github.com/example/project", "main", "aiseo/fix-x", [], "title", "body"
            )


async def test_get_default_branch_classifies_bad_credentials_as_auth():
    mock_client = MagicMock()
    mock_client.get_repo.side_effect = BadCredentialsException(401, {"message": "Bad credentials"}, None)

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="bad-token")
        with pytest.raises(GitHubOperationError) as exc_info:
            await provider.get_default_branch("https://github.com/example/project")

    assert exc_info.value.kind == ExternalErrorKind.AUTH
    assert "Bad credentials" not in exc_info.value.message


async def test_get_default_branch_classifies_unknown_object_as_not_found():
    mock_client = MagicMock()
    mock_client.get_repo.side_effect = UnknownObjectException(404, {"message": "Not Found"}, None)

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="test-token")
        with pytest.raises(GitHubOperationError) as exc_info:
            await provider.get_default_branch("https://github.com/example/project")

    assert exc_info.value.kind == ExternalErrorKind.NOT_FOUND


async def test_get_default_branch_classifies_rate_limit_exceeded():
    mock_client = MagicMock()
    mock_client.get_repo.side_effect = RateLimitExceededException(403, {"message": "API rate limit exceeded"}, None)

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="test-token")
        with pytest.raises(GitHubOperationError) as exc_info:
            await provider.get_default_branch("https://github.com/example/project")

    assert exc_info.value.kind == ExternalErrorKind.RATE_LIMIT


async def test_get_default_branch_classifies_connection_error_as_network():
    mock_client = MagicMock()
    mock_client.get_repo.side_effect = requests.exceptions.ConnectionError("connection refused")

    with patch("app.adapters.github.provider.Github", return_value=mock_client):
        provider = GitHubProvider(token="test-token")
        with pytest.raises(GitHubOperationError) as exc_info:
            await provider.get_default_branch("https://github.com/example/project")

    assert exc_info.value.kind == ExternalErrorKind.NETWORK
    assert "connection refused" not in exc_info.value.message
