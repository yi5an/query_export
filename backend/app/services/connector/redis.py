import json
from typing import Any, AsyncIterator, Dict, List

import redis.asyncio as redis
from redis.asyncio.cluster import ClusterNode

from app.services.connector.base import BaseConnector


class RedisConnector(BaseConnector):
    """Redis / Redis Cluster 连接器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    async def connect(self) -> None:
        cluster_nodes = self.config.get("cluster_nodes")
        if cluster_nodes:
            startup_nodes = []
            for node in cluster_nodes:
                host, port = str(node).split(":", 1)
                startup_nodes.append(ClusterNode(host, int(port)))
            self._client = redis.RedisCluster(
                startup_nodes=startup_nodes,
                username=self.config.get("username"),
                password=self.config.get("password"),
                ssl=bool(self.config.get("ssl", False)),
                decode_responses=True,
            )
        else:
            db_index = self.config.get("database")
            try:
                db_index = int(db_index) if db_index not in (None, "") else 0
            except (TypeError, ValueError):
                db_index = 0
            self._client = redis.Redis(
                host=self.config.get("host"),
                port=self.config.get("port", 6379),
                db=db_index,
                username=self.config.get("username"),
                password=self.config.get("password"),
                ssl=bool(self.config.get("ssl", False)),
                decode_responses=True,
            )
        await self._client.ping()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()

    async def test_connection(self) -> bool:
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    async def execute(self, command: str, limit: int = None) -> Dict[str, Any]:
        parts = command.strip().split()
        if not parts:
            return {"columns": [], "rows": [], "row_count": 0}

        cmd = parts[0].upper()
        args = parts[1:]
        result = await self._client.execute_command(cmd, *args)

        if isinstance(result, list):
            rows = [[self._stringify(item)] for item in (result[:limit] if limit else result)]
            columns = ["result"]
        elif isinstance(result, dict):
            items = list(result.items())
            if limit:
                items = items[:limit]
            rows = [[self._stringify(k), self._stringify(v)] for k, v in items]
            columns = ["key", "value"]
        else:
            rows = [[self._stringify(result)]]
            columns = ["result"]

        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }

    async def stream_execute(self, command: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        result = await self.execute(command)
        rows = result["rows"]
        for index in range(0, len(rows), batch_size):
            yield rows[index : index + batch_size]

    def get_export_formats(self) -> List[str]:
        return ["csv", "excel"]

    @staticmethod
    def _stringify(value: Any) -> Any:
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return json.dumps(value, ensure_ascii=False, default=str)
