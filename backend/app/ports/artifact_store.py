from typing import Protocol


class ArtifactStore(Protocol):
    """Port: object storage boundary for reports, screenshots, Lighthouse
    output, generated patches, large logs (docs/architecture.md §6/§8).
    """

    async def put(self, key: str, content: bytes) -> None: ...

    async def get(self, key: str) -> bytes | None: ...
