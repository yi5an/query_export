import asyncio
from typing import Any, AsyncIterator, Dict, List

import clickhouse_connect

from app.services.connector.base import BaseConnector
from app.services.sql_guard import ensure_readonly_query


class ClickHouseConnector(BaseConnector):
    """ClickHouse 连接器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    async def connect(self) -> None:
        self._client = await asyncio.to_thread(
            clickhouse_connect.get_client,
            host=self.config.get("host"),
            port=self.config.get("port", 8123),
            database=self.config.get("database") or "default",
            username=self.config.get("username") or "default",
            password=self.config.get("password"),
            secure=bool(self.config.get("ssl", False)),
        )

    async def close(self) -> None:
        if self._client:
            await asyncio.to_thread(self._client.close)

    async def test_connection(self) -> bool:
        try:
            await asyncio.to_thread(self._client.query, "SELECT 1")
            return True
        except Exception:
            return False

    async def execute(self, sql: str, limit: int = None) -> Dict[str, Any]:
        ensure_readonly_query(sql, "clickhouse")

        sql_stripped = sql.strip()
        sql_without_semicolon = sql_stripped.rstrip(";").strip()
        sql_upper = sql_stripped.upper()

        if limit and sql_upper.startswith("SELECT") and "LIMIT" not in sql_upper:
            sql = f"{sql_without_semicolon} LIMIT {limit}"

        result = await asyncio.to_thread(self._client.query, sql)
        return {
            "columns": list(result.column_names),
            "rows": [list(row) for row in result.result_rows],
            "row_count": len(result.result_rows),
        }

    async def stream_execute(self, sql: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        result = await asyncio.to_thread(self._client.query, sql)
        batch: list[list[Any]] = []
        for row in result.result_rows:
            batch.append(list(row))
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch

    def get_export_formats(self) -> List[str]:
        return ["csv", "excel", "sql"]
