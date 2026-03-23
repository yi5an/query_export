"""只读 SQL 校验服务。"""
from __future__ import annotations

import re

import sqlparse


SQL_DATASOURCE_TYPES = {"postgres", "postgresql", "clickhouse", "doris"}
READONLY_PREFIXES = ("SELECT", "WITH", "SHOW", "DESCRIBE", "DESC", "EXPLAIN")
FORBIDDEN_PATTERN = re.compile(
    r"\b("
    r"INSERT|UPDATE|DELETE|UPSERT|MERGE|REPLACE|CREATE|ALTER|DROP|TRUNCATE|"
    r"GRANT|REVOKE|CALL|EXEC|EXECUTE|COPY|VACUUM|ANALYZE|OPTIMIZE|SET|USE|"
    r"ATTACH|DETACH|SYSTEM|KILL|BEGIN|START\s+TRANSACTION|COMMIT|ROLLBACK"
    r")\b",
    re.IGNORECASE,
)
STRING_LITERAL_PATTERN = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"")


def is_sql_datasource(datasource_type: str) -> bool:
    return datasource_type in SQL_DATASOURCE_TYPES


def ensure_readonly_query(sql: str, datasource_type: str) -> None:
    """确保 SQL 类型数据源只执行单条只读语句。"""
    if not is_sql_datasource(datasource_type):
        return

    statements = [
        statement
        for statement in sqlparse.parse(sql)
        if statement.value.strip()
    ]
    if not statements:
        raise ValueError("SQL 不能为空")
    if len(statements) != 1:
        raise ValueError("仅允许执行单条只读查询语句")

    normalized_sql = sqlparse.format(sql, strip_comments=True).strip()
    if not normalized_sql:
        raise ValueError("SQL 不能为空")

    sanitized_sql = STRING_LITERAL_PATTERN.sub("''", normalized_sql)
    normalized_upper = sanitized_sql.upper()
    if not normalized_upper.startswith(READONLY_PREFIXES):
        raise ValueError("仅允许只读查询，支持 SELECT / WITH / SHOW / DESCRIBE / EXPLAIN")

    forbidden_match = FORBIDDEN_PATTERN.search(normalized_upper)
    if forbidden_match:
        raise ValueError(f"检测到非只读关键字: {forbidden_match.group(1).upper()}")
