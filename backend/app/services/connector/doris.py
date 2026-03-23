import asyncio
from typing import Any, AsyncIterator, Dict, List

import mysql.connector

from app.services.connector.base import BaseConnector
from app.services.sql_guard import ensure_readonly_query


class DorisConnector(BaseConnector):
    """Doris 连接器，使用 MySQL 协议。"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._connection = None

    async def connect(self) -> None:
        self._connection = await asyncio.to_thread(
            mysql.connector.connect,
            host=self.config.get("host"),
            port=self.config.get("port", 9030),
            database=self.config.get("database") or None,
            user=self.config.get("username") or "root",
            password=self.config.get("password"),
        )

    async def close(self) -> None:
        if self._connection and self._connection.is_connected():
            await asyncio.to_thread(self._connection.close)

    async def test_connection(self) -> bool:
        try:
            cursor = await asyncio.to_thread(self._connection.cursor)
            await asyncio.to_thread(cursor.execute, "SELECT 1")
            await asyncio.to_thread(cursor.fetchall)
            await asyncio.to_thread(cursor.close)
            return True
        except Exception:
            return False

    async def execute(self, sql: str, limit: int = None) -> Dict[str, Any]:
        ensure_readonly_query(sql, "doris")

        sql_stripped = sql.strip()
        sql_without_semicolon = sql_stripped.rstrip(";").strip()
        sql_upper = sql_stripped.upper()

        if limit and sql_upper.startswith("SELECT") and "LIMIT" not in sql_upper:
            sql = f"{sql_without_semicolon} LIMIT {limit}"

        cursor = await asyncio.to_thread(self._connection.cursor)
        try:
            await asyncio.to_thread(cursor.execute, sql)
            rows = await asyncio.to_thread(cursor.fetchall)
            columns = [column[0] for column in cursor.description] if cursor.description else []
            row_data = [list(row) for row in rows]

            return {
                "columns": columns,
                "rows": row_data,
                "row_count": len(row_data),
            }
        finally:
            await asyncio.to_thread(cursor.close)

    async def stream_execute(self, sql: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        cursor = await asyncio.to_thread(self._connection.cursor)
        try:
            await asyncio.to_thread(cursor.execute, sql)
            while True:
                rows = await asyncio.to_thread(cursor.fetchmany, batch_size)
                if not rows:
                    break
                yield [list(row) for row in rows]
        finally:
            await asyncio.to_thread(cursor.close)

    def get_export_formats(self) -> List[str]:
        return ["csv", "excel", "sql"]
