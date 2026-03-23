"""查询服务模块"""
import time
from typing import Dict, Any

from app.services.connector.factory import get_connector
from app.core.security import decrypt_password
from app.services.sql_guard import ensure_readonly_query


async def execute_query(
    datasource_type: str,
    config: Dict[str, Any],
    sql: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    执行查询

    Args:
        datasource_type: 数据源类型 (postgres, clickhouse 等)
        config: 连接配置，包含 host, port, database, username, password_encrypted 等
        sql: SQL 查询语句
        limit: 返回行数限制，默认 10

    Returns:
        查询结果，包含 columns, rows, row_count, execution_time_ms
    """
    # 复制配置以避免修改原始数据
    config = config.copy()

    # 解密密码
    if "password_encrypted" in config and config["password_encrypted"]:
        config["password"] = decrypt_password(config["password_encrypted"])
        del config["password_encrypted"]

    ensure_readonly_query(sql, datasource_type)

    connector = get_connector(datasource_type, config)
    await connector.connect()

    try:
        start_time = time.time()
        result = await connector.execute(sql, limit=limit)
        execution_time_ms = int((time.time() - start_time) * 1000)

        # 添加执行时间到结果
        result["execution_time_ms"] = execution_time_ms
        return result
    finally:
        await connector.close()


async def test_query(
    datasource_type: str,
    config: Dict[str, Any],
    sql: str
) -> bool:
    """
    测试查询是否可以执行

    Args:
        datasource_type: 数据源类型
        config: 连接配置
        sql: SQL 查询语句

    Returns:
        查询是否有效
    """
    try:
        await execute_query(datasource_type, config, sql, limit=1)
        return True
    except Exception:
        return False
