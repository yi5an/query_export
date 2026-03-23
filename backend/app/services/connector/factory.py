from typing import Dict, Any
from app.services.connector.base import BaseConnector
from app.services.connector.clickhouse import ClickHouseConnector
from app.services.connector.doris import DorisConnector
from app.services.connector.elasticsearch import ElasticsearchConnector
from app.services.connector.minio import MinioConnector
from app.services.connector.postgres import PostgresConnector
from app.services.connector.redis import RedisConnector

CONNECTOR_REGISTRY = {
    'postgres': PostgresConnector,
    'postgresql': PostgresConnector,  # alias
    'clickhouse': ClickHouseConnector,
    'doris': DorisConnector,
    'redis': RedisConnector,
    'redis-cluster': RedisConnector,
    'elasticsearch': ElasticsearchConnector,
    'minio': MinioConnector,
}


def get_connector(datasource_type: str, config: Dict[str, Any]) -> BaseConnector:
    """根据数据源类型获取连接器实例"""
    connector_class = CONNECTOR_REGISTRY.get(datasource_type)
    if not connector_class:
        supported = ", ".join(CONNECTOR_REGISTRY.keys())
        raise ValueError(f"Unsupported datasource type: {datasource_type}. Supported types: {supported}")
    return connector_class(config)


def get_supported_types() -> list[str]:
    return ["postgres", "clickhouse", "doris", "redis", "redis-cluster", "elasticsearch", "minio"]
