import asyncio
from pathlib import Path


class LocalFilesystemArtifactStore:
    """Adapter implementing the ArtifactStore port on local disk - for
    development, where Alibaba Cloud OSS credentials aren't available.
    Selected by `settings.artifact_store_backend == "local"` (see
    agents/bootstrap-style wiring in api/dependencies.py). Not a
    placeholder: a second real adapter for the same port, which is the
    entire point of the hexagonal ports/adapters split.
    """

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path

    def _resolve(self, key: str) -> Path:
        path = (self._base_path / key).resolve()
        if not str(path).startswith(str(self._base_path.resolve())):
            raise ValueError(f"Artifact key escapes the storage root: {key}")
        return path

    async def put(self, key: str, content: bytes) -> None:
        path = self._resolve(key)
        await asyncio.to_thread(self._write, path, content)

    def _write(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def get(self, key: str) -> bytes | None:
        path = self._resolve(key)
        return await asyncio.to_thread(self._read, path)

    def _read(self, path: Path) -> bytes | None:
        if not path.exists():
            return None
        return path.read_bytes()
