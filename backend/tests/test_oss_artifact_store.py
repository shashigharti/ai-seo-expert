from unittest.mock import MagicMock, patch

import pytest
from oss2.exceptions import NoSuchKey

from app.adapters.storage.oss_store import AlibabaOSSArtifactStore, OSSClientConfigurationError


def _store(**overrides) -> AlibabaOSSArtifactStore:
    defaults = dict(
        access_key_id="key-id",
        access_key_secret="key-secret",
        endpoint="https://oss-cn-hangzhou.aliyuncs.com",
        bucket_name="aiseo-artifacts",
    )
    defaults.update(overrides)
    return AlibabaOSSArtifactStore(**defaults)


async def test_put_raises_without_full_configuration():
    store = _store(access_key_id=None)
    with pytest.raises(OSSClientConfigurationError):
        await store.put("key", b"data")


async def test_get_raises_without_full_configuration():
    store = _store(bucket_name=None)
    with pytest.raises(OSSClientConfigurationError):
        await store.get("key")


async def test_put_calls_bucket_put_object():
    mock_bucket = MagicMock()
    with patch("app.adapters.storage.oss_store.oss2.Bucket", return_value=mock_bucket):
        await _store().put("reports/workflow-1.json", b'{"ok": true}')

    mock_bucket.put_object.assert_called_once_with("reports/workflow-1.json", b'{"ok": true}')


async def test_get_returns_content_on_success():
    mock_result = MagicMock()
    mock_result.read.return_value = b"file content"
    mock_bucket = MagicMock()
    mock_bucket.get_object.return_value = mock_result

    with patch("app.adapters.storage.oss_store.oss2.Bucket", return_value=mock_bucket):
        content = await _store().get("reports/workflow-1.json")

    assert content == b"file content"


async def test_get_returns_none_when_key_does_not_exist():
    mock_bucket = MagicMock()
    mock_bucket.get_object.side_effect = NoSuchKey(404, {}, "not found", {})

    with patch("app.adapters.storage.oss_store.oss2.Bucket", return_value=mock_bucket):
        content = await _store().get("missing.json")

    assert content is None
