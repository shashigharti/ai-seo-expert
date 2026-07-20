import uuid
from datetime import datetime, timezone

from app.domain.enums.memory_category import MemoryCategory
from app.domain.models.agent_result import Finding
from app.domain.models.memory_entry import MemoryEntry
from app.domain.policies.memory_expiration_policy import expiry_for
from app.domain.policies.memory_retrieval_policy import select_relevant_memory
from app.ports.repositories import MemoryRepository


class MemoryService:
    """docs/agent-architecture.md §12 - records concise decisions/evidence
    (never raw chain-of-thought) so future workflows on the same repository
    have context: known false positives to avoid re-flagging, and what's
    already been approved.
    """

    def __init__(self, memory_repository: MemoryRepository) -> None:
        self.memory_repository = memory_repository

    async def record_false_positive(self, repository_url: str, finding: Finding, rationale: str) -> MemoryEntry:
        return await self._record(
            repository_url,
            MemoryCategory.FALSE_POSITIVE,
            f"Reviewer rejected '{finding.title}' ({finding.category}): {rationale}",
        )

    async def record_approved_decision(
        self, repository_url: str, findings: list[Finding], pr_strategy: str
    ) -> list[MemoryEntry]:
        entries = []
        for finding in findings:
            entry = await self._record(
                repository_url,
                MemoryCategory.APPROVED_DECISION,
                f"Approved fix for '{finding.title}' ({finding.category}), pr_strategy={pr_strategy}",
            )
            entries.append(entry)
        return entries

    async def get_context_for_planning(self, repository_url: str) -> str:
        """Formats relevant memory as plain text for the SEO Manager's
        planning prompt - empty string (not an error) when there's nothing
        yet, which is the common case for a repository's first workflow.
        """
        all_entries = await self.memory_repository.list_for_repository(repository_url)
        relevant = select_relevant_memory(all_entries)
        if not relevant:
            return ""

        lines = [f"- [{e.category.value}] {e.content}" for e in relevant]
        return "Known context from previous analyses of this repository:\n" + "\n".join(lines)

    async def _record(self, repository_url: str, category: MemoryCategory, content: str) -> MemoryEntry:
        now = datetime.now(timezone.utc)
        entry = MemoryEntry(
            id=uuid.uuid4(),
            repository_url=repository_url,
            category=category,
            content=content,
            created_at=now,
            expires_at=expiry_for(category, now),
        )
        return await self.memory_repository.add(entry)
