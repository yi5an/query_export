"""导出服务模块"""
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.config import get_settings
from app.core.security import decrypt_password
from app.models.export_task import ExportTask as ExportTaskModel
from app.models.datasource import Datasource
from app.services.connector.factory import get_connector
from app.services.export.csv_handler import CSVHandler
from app.services.export.excel_handler import ExcelHandler
from app.services.export.sql_handler import SQLHandler
from app.services.sql_guard import ensure_readonly_query

settings = get_settings()
EXPORT_RETENTION_DAYS = 7

# 导出处理器映射
EXPORT_HANDLERS = {
    "csv": CSVHandler,
    "excel": ExcelHandler,
    "sql": SQLHandler,
}


async def get_datasource_config(db: AsyncSession, datasource_id: int) -> Optional[Dict[str, Any]]:
    """
    获取数据源配置并解密密码

    Args:
        db: 数据库会话
        datasource_id: 数据源 ID

    Returns:
        数据源配置字典，如果不存在则返回 None
    """
    result = await db.execute(
        select(Datasource).where(Datasource.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()

    if not datasource:
        return None

    config = {
        "host": datasource.host,
        "port": datasource.port,
        "database": datasource.database,
        "username": datasource.username,
    }

    # 解密密码
    if datasource.password_encrypted:
        config["password"] = decrypt_password(datasource.password_encrypted)

    if datasource.extra_config:
        config.update(datasource.extra_config)
    if datasource.type == "minio" and "secure" not in config:
        config["secure"] = bool(config.get("ssl", False))

    return {
        "type": datasource.type,
        "config": config
    }


async def execute_export_query(
    datasource_type: str,
    config: Dict[str, Any],
    sql: str
) -> Dict[str, Any]:
    """
    执行导出查询（不限制行数）

    Args:
        datasource_type: 数据源类型
        config: 连接配置
        sql: SQL 查询语句

    Returns:
        查询结果，包含 columns 和 rows
    """
    ensure_readonly_query(sql, datasource_type)

    connector = get_connector(datasource_type, config)
    await connector.connect()

    try:
        # 导出时不限制行数
        result = await connector.execute(sql, limit=None)
        return result
    finally:
        await connector.close()


async def create_export_task(
    db: AsyncSession,
    datasource_id: int,
    sql_text: str,
    export_format: str,
    saved_sql_id: Optional[int] = None
) -> ExportTaskModel:
    """
    创建导出任务

    Args:
        db: 数据库会话
        datasource_id: 数据源 ID
        sql_text: SQL 查询语句
        export_format: 导出格式 (csv/excel)
        saved_sql_id: 关联的保存 SQL ID

    Returns:
        创建的导出任务
    """
    task = ExportTaskModel(
        datasource_id=datasource_id,
        sql_text=sql_text,
        export_format=export_format,
        saved_sql_id=saved_sql_id,
        status="pending"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


async def run_export_task(db: AsyncSession, task_id: int) -> None:
    """
    执行导出任务（后台运行）

    Args:
        db: 数据库会话
        task_id: 导出任务 ID
    """
    # 获取任务
    result = await db.execute(
        select(ExportTaskModel).where(ExportTaskModel.id == task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        return

    try:
        # 更新状态为运行中
        task.status = "running"
        await db.commit()

        # 获取数据源配置
        datasource_info = await get_datasource_config(db, task.datasource_id)
        if not datasource_info:
            raise ValueError(f"Datasource {task.datasource_id} not found")

        # 执行查询
        query_result = await execute_export_query(
            datasource_info["type"],
            datasource_info["config"],
            task.sql_text
        )

        columns = query_result["columns"]
        rows = query_result["rows"]

        # 获取导出处理器
        handler_class = EXPORT_HANDLERS.get(task.export_format)
        if not handler_class:
            raise ValueError(f"Unsupported export format: {task.export_format}")

        # 生成文件路径
        export_dir = Path(settings.export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)

        filename = f"export_{task_id}_{uuid.uuid4().hex[:8]}{handler_class.get_extension()}"
        file_path = export_dir / filename

        # SQL 导出文件直接保存查询文本，其余格式导出查询结果
        if task.export_format == "sql":
            row_count = await handler_class.write(columns, rows, str(file_path), task.sql_text)
        else:
            row_count = await handler_class.write(columns, rows, str(file_path))

        # 更新任务状态
        task.status = "completed"
        task.file_path = str(file_path)
        task.row_count = row_count
        task.completed_at = datetime.utcnow()
        await db.commit()

    except Exception as e:
        # 更新任务状态为失败
        task.status = "failed"
        task.error_message = str(e)
        task.completed_at = datetime.utcnow()
        await db.commit()


async def run_export_task_in_background(task_id: int) -> None:
    """
    使用独立数据库会话执行导出任务，避免绑定到请求生命周期。
    """
    async with AsyncSessionLocal() as session:
        await run_export_task(session, task_id)


def get_export_expiry(task: ExportTaskModel) -> Optional[datetime]:
    if task.status not in {"completed", "failed"}:
        return None

    reference_time = task.completed_at or task.created_at
    if not reference_time:
        return None

    if reference_time.tzinfo is None:
        reference_time = reference_time.replace(tzinfo=timezone.utc)

    return reference_time + timedelta(days=EXPORT_RETENTION_DAYS)


def get_export_remaining_seconds(task: ExportTaskModel) -> Optional[int]:
    expires_at = get_export_expiry(task)
    if not expires_at:
        return None

    remaining = int((expires_at - datetime.now(timezone.utc)).total_seconds())
    return max(remaining, 0)


async def cleanup_expired_exports(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(ExportTaskModel).where(ExportTaskModel.status.in_(["completed", "failed"]))
    )
    tasks = result.scalars().all()

    deleted_count = 0
    for task in tasks:
        expires_at = get_export_expiry(task)
        if not expires_at or expires_at > now:
            continue

        if task.file_path:
            file_path = Path(task.file_path)
            if file_path.exists():
                file_path.unlink()

        await db.delete(task)
        deleted_count += 1

    if deleted_count:
        await db.commit()

    return deleted_count


async def execute_export_sync(
    db: AsyncSession,
    datasource_id: int,
    sql_text: str,
    export_format: str,
    saved_sql_id: Optional[int] = None
) -> ExportTaskModel:
    """
    同步执行导出任务（等待完成）

    Args:
        db: 数据库会话
        datasource_id: 数据源 ID
        sql_text: SQL 查询语句
        export_format: 导出格式
        saved_sql_id: 关联的保存 SQL ID

    Returns:
        完成的导出任务
    """
    # 创建任务
    task = await create_export_task(
        db, datasource_id, sql_text, export_format, saved_sql_id
    )

    # 同步执行
    await run_export_task(db, task.id)

    # 刷新任务状态
    await db.refresh(task)

    return task


async def get_export_task(db: AsyncSession, task_id: int) -> Optional[ExportTaskModel]:
    """
    获取导出任务

    Args:
        db: 数据库会话
        task_id: 任务 ID

    Returns:
        导出任务，如果不存在则返回 None
    """
    result = await db.execute(
        select(ExportTaskModel).where(ExportTaskModel.id == task_id)
    )
    return result.scalar_one_or_none()


async def list_export_tasks(
    db: AsyncSession,
    datasource_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50
) -> list[ExportTaskModel]:
    """
    获取导出任务列表

    Args:
        db: 数据库会话
        datasource_id: 数据源 ID 过滤
        status: 状态过滤
        limit: 返回数量限制

    Returns:
        导出任务列表
    """
    query = select(ExportTaskModel).order_by(ExportTaskModel.created_at.desc())

    if datasource_id:
        query = query.where(ExportTaskModel.datasource_id == datasource_id)

    if status:
        query = query.where(ExportTaskModel.status == status)

    query = query.limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


async def delete_export_task(db: AsyncSession, task_id: int) -> bool:
    """
    删除导出任务

    Args:
        db: 数据库会话
        task_id: 任务 ID

    Returns:
        是否删除成功
    """
    task = await get_export_task(db, task_id)

    if not task:
        return False

    # 如果任务正在运行，不能删除
    if task.status == "running":
        return False

    # 删除文件
    if task.file_path:
        file_path = Path(task.file_path)
        if file_path.exists():
            file_path.unlink()

    # 删除数据库记录
    await db.delete(task)
    await db.commit()

    return True


def get_export_file_info(task: ExportTaskModel) -> Optional[Dict[str, Any]]:
    """
    获取导出文件信息

    Args:
        task: 导出任务

    Returns:
        文件信息字典，如果文件不存在则返回 None
    """
    if not task.file_path:
        return None

    file_path = Path(task.file_path)

    if not file_path.exists():
        return None

    handler_class = EXPORT_HANDLERS.get(task.export_format)

    return {
        "filename": file_path.name,
        "content_type": handler_class.get_content_type() if handler_class else "application/octet-stream",
        "file_size": file_path.stat().st_size
    }
