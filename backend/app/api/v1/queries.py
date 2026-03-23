"""查询 API 模块"""
import sqlparse
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.api.deps import get_db_session
from app.models.datasource import Datasource as DatasourceModel
from app.services.query import execute_query
from app.services.sql_guard import ensure_readonly_query

router = APIRouter(tags=["查询"])


# ============ 请求/响应模型 ============

class QueryRequest(BaseModel):
    """查询请求"""
    datasource_id: int = Field(..., description="数据源 ID")
    sql: str = Field(..., description="SQL 查询语句")
    limit: int = Field(default=10, ge=1, le=10000, description="返回行数限制，默认 10，最大 10000")


class QueryResponse(BaseModel):
    """查询响应"""
    columns: List[str] = Field(..., description="列名列表")
    rows: List[List[Any]] = Field(..., description="数据行列表")
    row_count: int = Field(..., description="返回的行数")
    execution_time_ms: int = Field(..., description="执行时间（毫秒）")


class FormatRequest(BaseModel):
    """格式化请求"""
    sql: str = Field(..., description="SQL 查询语句")
    dialect: Optional[str] = Field(default=None, description="SQL 方言（如 postgresql, mysql 等）")


class FormatResponse(BaseModel):
    """格式化响应"""
    formatted_sql: str = Field(..., description="格式化后的 SQL")
    original_sql: str = Field(..., description="原始 SQL")


class ValidateRequest(BaseModel):
    """验证请求"""
    datasource_id: int = Field(..., description="数据源 ID")
    sql: str = Field(..., description="SQL 查询语句")


class ValidateResponse(BaseModel):
    """验证响应"""
    is_valid: bool = Field(..., description="SQL 是否有效")
    error: Optional[str] = Field(default=None, description="错误信息")


# ============ API 端点 ============

@router.post("/execute", response_model=QueryResponse)
async def execute_sql_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    执行 SQL 查询（试运行）

    执行 SQL 查询并返回结果，默认返回前 10 行数据。
    """
    # 获取数据源
    result = await db.execute(
        select(DatasourceModel).where(
            DatasourceModel.id == request.datasource_id,
            DatasourceModel.is_active == True
        )
    )
    datasource = result.scalar_one_or_none()

    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    # 构建连接配置
    config = {
        "host": datasource.host,
        "port": datasource.port,
        "database": datasource.database,
        "username": datasource.username,
        "password_encrypted": datasource.password_encrypted,
    }

    # 添加额外配置
    if datasource.extra_config:
        config.update(datasource.extra_config)
    if datasource.type == "minio" and "secure" not in config:
        config["secure"] = bool(config.get("ssl", False))

    try:
        # 执行查询
        query_result = await execute_query(
            datasource_type=datasource.type,
            config=config,
            sql=request.sql,
            limit=request.limit
        )

        return QueryResponse(
            columns=query_result["columns"],
            rows=query_result["rows"],
            row_count=query_result["row_count"],
            execution_time_ms=query_result["execution_time_ms"]
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Query execution failed: {str(e)}")


@router.post("/format", response_model=FormatResponse)
async def format_sql(request: FormatRequest):
    """
    格式化 SQL

    使用 sqlparse 库格式化 SQL 语句，使其更易读。
    """
    try:
        # 使用 sqlparse 格式化 SQL
        formatted = sqlparse.format(
            request.sql,
            keyword_case='upper',
            identifier_case='lower',
            reindent=True,
            indent_width=2,
            wrap_mode='word'
        )

        return FormatResponse(
            formatted_sql=formatted,
            original_sql=request.sql
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL formatting failed: {str(e)}")


@router.post("/validate", response_model=ValidateResponse)
async def validate_sql(
    request: ValidateRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """
    验证 SQL 语法

    验证 SQL 语句的基本语法是否正确（使用 sqlparse 进行静态分析）。
    注意：这只是基本的语法检查，不会执行查询。
    """
    try:
        result = await db.execute(
            select(DatasourceModel).where(
                DatasourceModel.id == request.datasource_id,
                DatasourceModel.is_active == True
            )
        )
        datasource = result.scalar_one_or_none()

        if not datasource:
            return ValidateResponse(
                is_valid=False,
                error="Datasource not found"
            )

        # 使用 sqlparse 解析 SQL
        parsed = sqlparse.parse(request.sql)

        if not parsed:
            return ValidateResponse(
                is_valid=False,
                error="Empty or invalid SQL statement"
            )

        # 检查是否有有效的语句
        for statement in parsed:
            # 检查语句类型
            if statement.get_type() == 'UNKNOWN':
                # 进一步检查是否为空或只有注释
                stripped = statement.value.strip()
                if not stripped:
                    return ValidateResponse(
                        is_valid=False,
                        error="Empty SQL statement"
                    )

        # 基本语法检查通过
        ensure_readonly_query(request.sql, datasource.type)

        return ValidateResponse(
            is_valid=True,
            error=None
        )

    except Exception as e:
        return ValidateResponse(
            is_valid=False,
            error=str(e)
        )
