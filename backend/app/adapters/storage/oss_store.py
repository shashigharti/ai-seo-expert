import asyncio

import oss2
from oss2.exceptions import NoSuchKey


class OSSClientConfigurationError(Exception):
    """Raised when Alibaba Cloud OSS credentials are missing at call time."""


class AlibabaOSSArtifactStore:
    """Adapter implementing the ArtifactStore port via Alibaba Cloud Object
    Storage Service - docs/architecture.md §6/§8 names this
    AlibabaOSSArtifactStore. oss2 is synchronous; real work runs via
    `asyncio.to_thread`, same reasoning as GitHubProvider (Phase 8).
    """

    def __init__(
        self,
        access_key_id: str | None,
        access_key_secret: str | None,
        endpoint: str | None,
        bucket_name: str | None,
    ) -> None:
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._endpoint = endpoint
        self._bucket_name = bucket_name

    def _bucket(self) -> oss2.Bucket:
        if not all([self._access_key_id, self._access_key_secret, self._endpoint, self._bucket_name]):
            raise OSSClientConfigurationError(
                "OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET, OSS_ENDPOINT, and OSS_BUCKET must "
                "all be set to use Alibaba Cloud OSS storage - see docs/deployment.md."
            )
        auth = oss2.Auth(self._access_key_id, self._access_key_secret)
        return oss2.Bucket(auth, self._endpoint, self._bucket_name)

    async def put(self, key: str, content: bytes) -> None:
        bucket = self._bucket()
        await asyncio.to_thread(bucket.put_object, key, content)

    async def get(self, key: str) -> bytes | None:
        bucket = self._bucket()
        return await asyncio.to_thread(self._get_sync, bucket, key)

    def _get_sync(self, bucket: oss2.Bucket, key: str) -> bytes | None:
        try:
            return bucket.get_object(key).read()
        except NoSuchKey:
            return None
