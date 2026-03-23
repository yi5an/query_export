import asyncpg
import logging
from typing import AsyncIterator, Any, Dict, List
from app.services.connector.base import BaseConnector
from app.services.sql_guard import ensure_readonly_query

logger = logging.getLogger(__name__)


class PostgresConnector(BaseConnector):
    """PostgreSQL 连接器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._pool = None

    async def connect(self) -> None:
        """建立连接池"""
        self._pool = await asyncpg.create_pool(
            host=self.config.get('host'),
            port=self.config.get('port', 5432),
            database=self.config.get('database'),
            user=self.config.get('username'),
            password=self.config.get('password'),
            min_size=1,
            max_size=5
        )

    async def close(self) -> None:
        """关闭连接池"""
        if self._pool:
            await self._pool.close()

    async def test_connection(self) -> bool:
        """测试连接"""
        if not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False

    async def execute(self, sql: str, limit: int = None) -> Dict[str, Any]:
        """执行查询"""
        ensure_readonly_query(sql, "postgres")

        sql_stripped = sql.strip()
        sql_without_semicolon = sql_stripped.rstrip(";").strip()
        sql_upper = sql_stripped.upper()

        # 只对 SELECT 查询添加 LIMIT
        is_select = sql_upper.startswith("SELECT")
        if is_select and limit and "LIMIT" not in sql_upper:
            sql = f"{sql_without_semicolon} LIMIT {limit}"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql)
            if rows:
                columns = list(rows[0].keys())
                row_data = [list(row.values()) for row in rows]
            else:
                columns = []
                row_data = []

            return {
                "columns": columns,
                "rows": row_data,
                "row_count": len(row_data)
            }

    async def stream_execute(self, sql: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        """流式执行"""
        async with self._pool.acquire() as conn:
            cursor = conn.cursor(sql)
            while True:
                batch = await cursor.fetch(batch_size)
                if not batch:
                    break
                yield [list(row.values()) for row in batch]

    def get_export_formats(self) -> List[str]:
        """支持的导出格式"""
        return ["csv", "excel", "sql"]
