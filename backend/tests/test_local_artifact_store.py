from pathlib import Path

import pytest

from app.adapters.storage.local_store import LocalFilesystemArtifactStore


@pytest.fixture
def store(tmp_path: Path) -> LocalFilesystemArtifactStore:
    return LocalFilesystemArtifactStore(base_path=tmp_path)


async def test_put_then_get_returns_the_same_content(store: LocalFilesystemArtifactStore):
    await store.put("reports/workflow-1/report.json", b'{"total_findings": 3}')

    content = await store.get("reports/workflow-1/report.json")

    assert content == b'{"total_findings": 3}'


async def test_get_returns_none_for_missing_key(store: LocalFilesystemArtifactStore):
    assert await store.get("does/not/exist.txt") is None


async def test_put_creates_intermediate_directories(store: LocalFilesystemArtifactStore, tmp_path: Path):
    await store.put("a/b/c/file.txt", b"data")
    assert (tmp_path / "a" / "b" / "c" / "file.txt").exists()


async def test_put_rejects_path_traversal(store: LocalFilesystemArtifactStore):
    with pytest.raises(ValueError):
        await store.put("../../etc/passwd", b"malicious")
