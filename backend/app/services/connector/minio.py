import asyncio
from datetime import timedelta
from typing import Any, AsyncIterator, Dict, List

from minio import Minio

from app.services.connector.base import BaseConnector


class MinioConnector(BaseConnector):
    """MinIO 对象存储连接器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    async def connect(self) -> None:
        self._client = Minio(
            f"{self.config.get('host')}:{self.config.get('port', 9000)}",
            access_key=self.config.get("username"),
            secret_key=self.config.get("password"),
            secure=bool(self.config.get("secure", False)),
        )
        await asyncio.to_thread(list, self._client.list_buckets())

    async def close(self) -> None:
        return None

    async def test_connection(self) -> bool:
        try:
            await asyncio.to_thread(list, self._client.list_buckets())
            return True
        except Exception:
            return False

    async def execute(self, path: str, limit: int = None) -> Dict[str, Any]:
        bucket, prefix = self._split_path(path)
        objects = await asyncio.to_thread(
            lambda: list(self._client.list_objects(bucket, prefix=prefix, recursive=False))
        )
        rows = []
        for obj in objects[: limit or None]:
            rows.append([obj.object_name, obj.size, obj.last_modified, obj.etag])

        return {
            "columns": ["name", "size", "last_modified", "etag"],
            "rows": rows,
            "row_count": len(rows),
        }

    async def stream_execute(self, path: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        bucket, prefix = self._split_path(path)
        objects = await asyncio.to_thread(
            lambda: list(self._client.list_objects(bucket, prefix=prefix, recursive=True))
        )
        batch: list[list[Any]] = []
        for obj in objects:
            batch.append([obj.object_name, obj.size, obj.last_modified, obj.etag])
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def get_export_formats(self) -> List[str]:
        return []

    async def get_presigned_url(self, bucket: str, object_name: str, expires: int = 3600) -> str:
        return await asyncio.to_thread(
            self._client.presigned_get_object,
            bucket,
            object_name,
            expires=timedelta(seconds=expires),
        )

    @staticmethod
    def _split_path(path: str) -> tuple[str, str]:
        parts = path.split("/", 1)
        bucket = parts[0]
        prefix = parts[1] if len(parts) > 1 else ""
        return bucket, prefix
