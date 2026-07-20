from typing import Protocol

from app.domain.models.patch import ProposedPatch


class GitProvider(Protocol):
    """Port: version control boundary for opening fix PRs
    (docs/architecture.md §6 Hexagonal Ports names this GitProvider).
    """

    async def get_default_branch(self, repository_url: str) -> str: ...

    async def open_pull_request(
        self,
        repository_url: str,
        base_branch: str,
        new_branch: str,
        patches: list[ProposedPatch],
        pr_title: str,
        pr_body: str,
    ) -> str:
        """Creates a branch off base_branch, commits each patch, opens a PR.
        Returns the PR URL."""
        ...
