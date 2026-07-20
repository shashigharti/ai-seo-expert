import asyncio

import requests
from github import Auth, Github
from github.GithubException import (
    BadCredentialsException,
    GithubException,
    RateLimitExceededException,
    UnknownObjectException,
)

from app.config.logging import get_logger
from app.domain.errors import ExternalErrorKind, ExternalServiceError
from app.domain.models.patch import ProposedPatch
from app.tools.github_file_reader import parse_owner_repo

logger = get_logger(__name__)


class GitHubClientConfigurationError(ExternalServiceError):
    """Raised when GITHUB_TOKEN is missing at call time."""

    def __init__(self, message: str) -> None:
        super().__init__(service="GitHub", kind=ExternalErrorKind.AUTH, message=message)


class GitHubOperationError(ExternalServiceError):
    """Raised when a GitHub API call fails after credentials were present."""

    def __init__(self, kind: ExternalErrorKind, message: str) -> None:
        super().__init__(service="GitHub", kind=kind, message=message)


def _classify_github_exception(exc: GithubException) -> GitHubOperationError:
    """Turns a raw PyGithub exception into a curated, user-safe
    GitHubOperationError - never the raw stringified exception (which is
    GitHub's JSON error body verbatim, e.g. `401 {"message": "Bad
    credentials", ...}`).
    """
    if isinstance(exc, RateLimitExceededException):
        return GitHubOperationError(
            ExternalErrorKind.RATE_LIMIT,
            "GitHub API rate limit exceeded. Wait a while before trying again.",
        )
    if isinstance(exc, BadCredentialsException) or exc.status in (401, 403):
        return GitHubOperationError(
            ExternalErrorKind.AUTH,
            "GitHub rejected the configured GITHUB_TOKEN. Check that it's valid and has the "
            "required repository permissions.",
        )
    if isinstance(exc, UnknownObjectException) or exc.status == 404:
        return GitHubOperationError(
            ExternalErrorKind.NOT_FOUND,
            "The repository or branch was not found on GitHub. Check the repository URL and branch name.",
        )
    data_message = exc.data.get("message") if isinstance(exc.data, dict) else None
    return GitHubOperationError(
        ExternalErrorKind.UNKNOWN,
        f"GitHub rejected the request: {data_message}" if data_message else "The GitHub API request failed.",
    )


def _classify_network_exception() -> GitHubOperationError:
    return GitHubOperationError(
        ExternalErrorKind.NETWORK,
        "Could not reach GitHub - check your network connection and try again.",
    )


class GitHubProvider:
    """Adapter implementing the GitProvider port via the real GitHub REST
    API (PyGithub) - docs/architecture.md §6 names this GitHubProvider.

    Uses a personal access token (GITHUB_TOKEN), not the GitHub App
    credentials docs/deployment.md originally listed - see
    review/CHANGELOG.md Phase 8 notes for why (simpler, matches the
    hackathon-demo framing in docs/implementation.md, still real).

    PyGithub is synchronous (blocking HTTP under the hood); the actual work
    runs via `asyncio.to_thread` so it doesn't stall the event loop that's
    also serving SSE streams and other requests.
    """

    def __init__(self, token: str | None) -> None:
        self._token = token

    def _require_token(self) -> str:
        if not self._token:
            raise GitHubClientConfigurationError(
                "GITHUB_TOKEN is not set. Configure it in .env to open pull requests "
                "- see docs/deployment.md."
            )
        return self._token

    async def get_default_branch(self, repository_url: str) -> str:
        self._require_token()
        return await asyncio.to_thread(self._get_default_branch_sync, repository_url)

    def _get_default_branch_sync(self, repository_url: str) -> str:
        owner, repo_name = parse_owner_repo(repository_url)
        client = Github(auth=Auth.Token(self._token))
        try:
            return client.get_repo(f"{owner}/{repo_name}").default_branch
        except GithubException as exc:
            raise _classify_github_exception(exc) from exc
        except requests.exceptions.RequestException as exc:
            raise _classify_network_exception() from exc
        finally:
            client.close()

    async def open_pull_request(
        self,
        repository_url: str,
        base_branch: str,
        new_branch: str,
        patches: list[ProposedPatch],
        pr_title: str,
        pr_body: str,
    ) -> str:
        self._require_token()
        return await asyncio.to_thread(
            self._open_pull_request_sync, repository_url, base_branch, new_branch, patches, pr_title, pr_body
        )

    def _open_pull_request_sync(
        self,
        repository_url: str,
        base_branch: str,
        new_branch: str,
        patches: list[ProposedPatch],
        pr_title: str,
        pr_body: str,
    ) -> str:
        owner, repo_name = parse_owner_repo(repository_url)
        client = Github(auth=Auth.Token(self._token))

        try:
            repo = client.get_repo(f"{owner}/{repo_name}")
            base_sha = repo.get_branch(base_branch).commit.sha
            repo.create_git_ref(ref=f"refs/heads/{new_branch}", sha=base_sha)

            for patch in patches:
                try:
                    existing = repo.get_contents(patch.file_path, ref=new_branch)
                    sha = existing.sha if not isinstance(existing, list) else existing[0].sha
                    repo.update_file(
                        path=patch.file_path,
                        message=patch.commit_message,
                        content=patch.new_content,
                        sha=sha,
                        branch=new_branch,
                    )
                except UnknownObjectException:
                    repo.create_file(
                        path=patch.file_path,
                        message=patch.commit_message,
                        content=patch.new_content,
                        branch=new_branch,
                    )

            pull_request = repo.create_pull(
                base=base_branch, head=new_branch, title=pr_title, body=pr_body
            )
            return pull_request.html_url
        except GithubException as exc:
            logger.exception("GitHub operation failed for %s", repository_url)
            raise _classify_github_exception(exc) from exc
        except requests.exceptions.RequestException as exc:
            logger.exception("GitHub network error for %s", repository_url)
            raise _classify_network_exception() from exc
        finally:
            client.close()
