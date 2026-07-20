import re

import httpx

from app.domain.errors import ExternalErrorKind, ExternalServiceError

_GITHUB_URL_PATTERN = re.compile(r"github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$")

# Common non-source directories excluded from list_repository_files -
# noise a manager would never want to plan scope.files against.
_EXCLUDED_DIR_PREFIXES = (
    "node_modules/",
    ".git/",
    "dist/",
    "build/",
    "vendor/",
    ".next/",
    "__pycache__/",
)
_MAX_LISTED_FILES = 300


class InvalidRepositoryUrlError(Exception):
    pass


def parse_owner_repo(repository_url: str) -> tuple[str, str]:
    match = _GITHUB_URL_PATTERN.search(repository_url)
    if not match:
        raise InvalidRepositoryUrlError(f"Not a recognizable GitHub repository URL: {repository_url}")
    return match.group("owner"), match.group("repo")


def _raise_network_error(exc: Exception) -> None:
    raise ExternalServiceError(
        service="GitHub",
        kind=ExternalErrorKind.NETWORK,
        message="Could not reach GitHub - check your network connection and try again.",
    ) from exc


def _raise_for_github_api_error(response: httpx.Response, action: str) -> None:
    if response.status_code == 429:
        raise ExternalServiceError(
            service="GitHub",
            kind=ExternalErrorKind.RATE_LIMIT,
            message="GitHub API rate limit exceeded. Wait a while before trying again.",
        )
    if response.status_code in (401, 403):
        raise ExternalServiceError(
            service="GitHub",
            kind=ExternalErrorKind.AUTH,
            message=f"GitHub rejected the request while {action}.",
        )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ExternalServiceError(
            service="GitHub",
            kind=ExternalErrorKind.UNKNOWN,
            message=f"GitHub rejected the request while {action}.",
        ) from exc


async def read_repository_file(repository_url: str, path: str, ref: str = "HEAD") -> str | None:
    """Fetch a single file's raw content from a public GitHub repository.

    Real HTTP call against GitHub's raw content endpoint (same approach used
    earlier in this project to inspect real repositories) - no
    fabricated/simulated content. Returns None if the file doesn't exist at
    that ref (a normal, expected outcome - e.g. a repo with no robots.txt),
    not an error.
    """
    owner, repo = parse_owner_repo(repository_url)
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path.lstrip('/')}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        _raise_network_error(exc)

    if response.status_code == 404:
        return None
    _raise_for_github_api_error(response, action="reading repository content")
    return response.text


async def list_repository_files(repository_url: str, ref: str = "HEAD") -> list[str]:
    """List every file path in a repository at a given ref, via GitHub's
    recursive Git Trees API - one request instead of walking directories
    one at a time (which is what was missing before: nothing anywhere in
    this pipeline could see the real repository tree, so the SEO Manager
    was planning scope.files from guessed conventional filenames alone).

    Excludes common non-source directories and caps the result
    (_MAX_LISTED_FILES) to keep prompt size bounded. If GitHub reports the
    tree as truncated (very large repos), still returns what it gave back
    rather than failing - a real, disclosed limitation, not pretended
    completeness.
    """
    owner, repo = parse_owner_repo(repository_url)
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{ref}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                params={"recursive": "1"},
                # api.github.com (unlike raw.githubusercontent.com) rejects
                # requests with no User-Agent header at all.
                headers={"Accept": "application/vnd.github+json", "User-Agent": "aiseo-expert-agent"},
            )
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        _raise_network_error(exc)

    if response.status_code == 404:
        raise ExternalServiceError(
            service="GitHub",
            kind=ExternalErrorKind.NOT_FOUND,
            message="The repository or branch was not found on GitHub. Check the repository URL and branch name.",
        )
    _raise_for_github_api_error(response, action="listing repository files")

    data = response.json()
    paths = [
        entry["path"]
        for entry in data.get("tree", [])
        if entry.get("type") == "blob" and not entry["path"].startswith(_EXCLUDED_DIR_PREFIXES)
    ]
    return paths[:_MAX_LISTED_FILES]
