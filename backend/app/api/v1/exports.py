from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.api.deps import get_db_session
from app.schemas.export_task import ExportTaskCreate, ExportTask as ExportTaskSchema
from app.models.export_task import ExportTask as ExportTaskModel
from app.models.datasource import Datasource
from app.services import export_service
from app.services.sql_guard import ensure_readonly_query

router = APIRouter(tags=["导出"])


def _to_schema(task: ExportTaskModel, datasource_name: Optional[str] = None) -> ExportTaskSchema:
    return ExportTaskSchema(
        id=task.id,
        datasource_id=task.datasource_id,
        datasource_name=datasource_name,
        sql_text=task.sql_text,
        export_format=task.export_format,
        status=task.status,
        file_path=task.file_path,
        row_count=task.row_count,
        error_message=task.error_message,
        created_at=task.created_at,
        completed_at=task.completed_at,
        expires_at=export_service.get_export_expiry(task),
        remaining_seconds=export_service.get_export_remaining_seconds(task),
    )


@router.post("/", response_model=ExportTaskSchema)
async def create_export(
    background_tasks: BackgroundTasks,
    export_data: ExportTaskCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    创建导出任务并异步执行

    - **datasource_id**: 数据源 ID
    - **sql_text**: SQL 查询语句
    - **export_format**: 导出格式 (csv/excel/sql)
    - **saved_sql_id**: 可选，关联的保存 SQL ID
    """
    # 验证导出格式
    if export_data.export_format not in ["csv", "excel", "sql"]:
        raise HTTPException(
            status_code=400,
            detail="Unsupported export format. Supported formats: csv, excel, sql"
        )

    result = await db.execute(
        select(Datasource).where(
            Datasource.id == export_data.datasource_id,
            Datasource.is_active == True,
        )
    )
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    try:
        ensure_readonly_query(export_data.sql_text, datasource.type)
        await export_service.cleanup_expired_exports(db)
        task = await export_service.create_export_task(
            db=db,
            datasource_id=export_data.datasource_id,
            sql_text=export_data.sql_text,
            export_format=export_data.export_format,
            saved_sql_id=export_data.saved_sql_id
        )
        background_tasks.add_task(export_service.run_export_task_in_background, task.id)
        return _to_schema(task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@router.get("/", response_model=List[ExportTaskSchema])
async def list_exports(
    datasource_id: Optional[int] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取导出任务列表

    - **datasource_id**: 可选，按数据源过滤
    - **status**: 可选，按状态过滤 (pending/running/completed/failed)
    - **limit**: 返回数量限制，默认 50
    """
    await export_service.cleanup_expired_exports(db)

    tasks = await export_service.list_export_tasks(
        db=db,
        datasource_id=datasource_id,
        status=status,
        limit=limit
    )

    # 获取数据源名称映射
    datasource_names = {}
    result = await db.execute(select(Datasource.id, Datasource.name))
    for row in result:
        datasource_names[row[0]] = row[1]

    # 为每个任务添加数据源名称
    task_list = []
    for task in tasks:
        task_list.append(_to_schema(task, datasource_names.get(task.datasource_id)))

    return task_list


@router.get("/{task_id}", response_model=ExportTaskSchema)
async def get_export(
    task_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    获取导出任务状态

    - **task_id**: 任务 ID
    """
    await export_service.cleanup_expired_exports(db)
    task = await export_service.get_export_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Export task not found")

    datasource_name = None
    if task.datasource_id:
        result = await db.execute(select(Datasource.name).where(Datasource.id == task.datasource_id))
        datasource_name = result.scalar_one_or_none()

    return _to_schema(task, datasource_name)


@router.get("/{task_id}/download")
async def download_export(
    task_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    下载导出文件

    - **task_id**: 任务 ID
    """
    await export_service.cleanup_expired_exports(db)
    task = await export_service.get_export_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Export task not found")

    if task.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Export task is not completed. Current status: {task.status}"
        )

    file_info = export_service.get_export_file_info(task)

    if not file_info:
        raise HTTPException(status_code=404, detail="Export file not found")

    return FileResponse(
        path=task.file_path,
        filename=file_info["filename"],
        media_type=file_info["content_type"]
    )


@router.delete("/{task_id}")
async def delete_export(
    task_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """
    取消/删除导出任务

    - **task_id**: 任务 ID
    """
    task = await export_service.get_export_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Export task not found")

    if task.status == "running":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a running export task"
        )

    deleted = await export_service.delete_export_task(db, task_id)

    if not deleted:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete export task"
        )

    return {"message": "Export task deleted"}
