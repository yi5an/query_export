import json
from typing import Any, AsyncIterator, Dict, List

from elasticsearch import AsyncElasticsearch

from app.services.connector.base import BaseConnector


class ElasticsearchConnector(BaseConnector):
    """Elasticsearch 连接器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._client = None

    async def connect(self) -> None:
        scheme = "https" if self.config.get("ssl", False) else "http"
        host = {
            "host": self.config.get("host"),
            "port": self.config.get("port", 9200),
            "scheme": scheme,
        }
        kwargs: dict[str, Any] = {"hosts": [host], "verify_certs": bool(self.config.get("ssl", False))}

        if self.config.get("username"):
            kwargs["basic_auth"] = (self.config.get("username"), self.config.get("password"))
        if self.config.get("api_key"):
            kwargs["api_key"] = self.config.get("api_key")

        self._client = AsyncElasticsearch(**kwargs)
        await self._client.ping()

    async def close(self) -> None:
        if self._client:
            await self._client.close()

    async def test_connection(self) -> bool:
        try:
            return bool(await self._client.ping())
        except Exception:
            return False

    async def execute(self, query: str, limit: int = None) -> Dict[str, Any]:
        index = self.config.get("index_pattern") or self.config.get("database") or "*"
        body = self._parse_query(query)
        body.setdefault("size", limit or 10)

        result = await self._client.search(index=index, body=body)
        columns: list[str] = []
        rows: list[list[Any]] = []

        for hit in result["hits"]["hits"]:
            source = hit.get("_source", {})
            if not columns:
                columns = list(source.keys())
            rows.append([source.get(column) for column in columns])

        total = result["hits"]["total"]
        total_value = total["value"] if isinstance(total, dict) else total
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "total": total_value,
        }

    async def stream_execute(self, query: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        index = self.config.get("index_pattern") or self.config.get("database") or "*"
        body = self._parse_query(query)
        body["size"] = batch_size

        response = await self._client.search(index=index, body=body, scroll="2m")
        scroll_id = response.get("_scroll_id")

        try:
            while True:
                hits = response["hits"]["hits"]
                if not hits:
                    break

                columns: list[str] = []
                batch: list[list[Any]] = []
                for hit in hits:
                    source = hit.get("_source", {})
                    if not columns:
                        columns = list(source.keys())
                    batch.append([source.get(column) for column in columns])

                yield batch

                if len(hits) < batch_size or not scroll_id:
                    break
                response = await self._client.scroll(scroll_id=scroll_id, scroll="2m")
                scroll_id = response.get("_scroll_id", scroll_id)
        finally:
            if scroll_id:
                await self._client.clear_scroll(scroll_id=scroll_id)

    def get_export_formats(self) -> List[str]:
        return ["csv", "excel", "json"]

    @staticmethod
    def _parse_query(query: str) -> Dict[str, Any]:
        try:
            return json.loads(query)
        except json.JSONDecodeError:
            return {"query": {"query_string": {"query": query}}}
