from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.models.datasource import Datasource as DatasourceModel
from app.models.saved_sql import SavedSql as SavedSqlModel
from app.schemas.saved_sql import SavedSql as SavedSqlSchema, SavedSqlCreate, SavedSqlUpdate
from app.services.ai_service import (
    build_saved_sql_embedding_text,
    generate_embedding_with_settings,
    get_active_ai_config,
    get_embedding_settings,
)
from app.services.sql_guard import ensure_readonly_query

router = APIRouter()


def _to_schema(model: SavedSqlModel) -> SavedSqlSchema:
    return SavedSqlSchema(
        id=model.id,
        datasource_id=model.datasource_id,
        name=model.name,
        sql_text=model.sql_text,
        comment=model.comment,
        tags=model.tags or [],
        run_count=model.run_count or 0,
        last_run_at=model.last_run_at.isoformat() if model.last_run_at else None,
        created_at=model.created_at.isoformat() if model.created_at else "",
        updated_at=model.updated_at.isoformat() if model.updated_at else "",
    )


async def _get_datasource_or_404(db: AsyncSession, datasource_id: int) -> DatasourceModel:
    result = await db.execute(
        select(DatasourceModel).where(
            DatasourceModel.id == datasource_id,
            DatasourceModel.is_active == True,
        )
    )
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    return datasource


@router.get("/", response_model=List[SavedSqlSchema])
async def list_saved_sqls(
    datasource_id: Optional[int] = None,
    search: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
):
    query = select(SavedSqlModel)

    if datasource_id:
        query = query.where(SavedSqlModel.datasource_id == datasource_id)

    if search:
        keyword = f"%{search}%"
        query = query.where(
            or_(
                SavedSqlModel.name.ilike(keyword),
                SavedSqlModel.comment.ilike(keyword),
                SavedSqlModel.sql_text.ilike(keyword),
            )
        )

    query = query.order_by(SavedSqlModel.updated_at.desc(), SavedSqlModel.id.desc())
    result = await db.execute(query)
    return [_to_schema(item) for item in result.scalars().all()]


@router.get("/{sql_id}", response_model=SavedSqlSchema)
async def get_saved_sql(sql_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(SavedSqlModel).where(SavedSqlModel.id == sql_id))
    saved_sql = result.scalar_one_or_none()
    if not saved_sql:
        raise HTTPException(status_code=404, detail="Saved SQL not found")
    return _to_schema(saved_sql)


@router.post("/", response_model=SavedSqlSchema)
async def create_saved_sql(payload: SavedSqlCreate, db: AsyncSession = Depends(get_db_session)):
    try:
        datasource = await _get_datasource_or_404(db, payload.datasource_id)
        ensure_readonly_query(payload.sql_text, datasource.type)

        payload_data = payload.model_dump()
        ai_config = await get_active_ai_config(db)
        payload_data["embedding"] = await generate_embedding_with_settings(
            build_saved_sql_embedding_text(
                name=payload.name,
                sql_text=payload.sql_text,
                comment=payload.comment,
                tags=payload.tags or [],
            ),
            get_embedding_settings(ai_config),
        )
        item = SavedSqlModel(**payload_data)
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return _to_schema(item)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/{sql_id}", response_model=SavedSqlSchema)
async def update_saved_sql(sql_id: int, payload: SavedSqlUpdate, db: AsyncSession = Depends(get_db_session)):
    try:
        result = await db.execute(select(SavedSqlModel).where(SavedSqlModel.id == sql_id))
        saved_sql = result.scalar_one_or_none()
        if not saved_sql:
            raise HTTPException(status_code=404, detail="Saved SQL not found")

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(saved_sql, field, value)

        datasource = await _get_datasource_or_404(db, saved_sql.datasource_id)
        ensure_readonly_query(saved_sql.sql_text, datasource.type)

        ai_config = await get_active_ai_config(db)
        saved_sql.embedding = await generate_embedding_with_settings(
            build_saved_sql_embedding_text(
                name=saved_sql.name,
                sql_text=saved_sql.sql_text,
                comment=saved_sql.comment,
                tags=saved_sql.tags or [],
            ),
            get_embedding_settings(ai_config),
        )

        await db.commit()
        await db.refresh(saved_sql)
        return _to_schema(saved_sql)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{sql_id}")
async def delete_saved_sql(sql_id: int, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(SavedSqlModel).where(SavedSqlModel.id == sql_id))
    saved_sql = result.scalar_one_or_none()
    if not saved_sql:
        raise HTTPException(status_code=404, detail="Saved SQL not found")

    await db.delete(saved_sql)
    await db.commit()
    return {"message": "Saved SQL deleted"}


@router.post("/{sql_id}/run")
async def run_saved_sql(
    sql_id: int,
    limit: int = 10,
    db: AsyncSession = Depends(get_db_session),
):
    from app.services.query import execute_query

    result = await db.execute(select(SavedSqlModel).where(SavedSqlModel.id == sql_id))
    saved_sql = result.scalar_one_or_none()
    if not saved_sql:
        raise HTTPException(status_code=404, detail="Saved SQL not found")

    ds_result = await db.execute(select(DatasourceModel).where(DatasourceModel.id == saved_sql.datasource_id))
    datasource = ds_result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    saved_sql.run_count = (saved_sql.run_count or 0) + 1
    saved_sql.last_run_at = datetime.utcnow()
    await db.commit()

    config = {
        "host": datasource.host,
        "port": datasource.port,
        "database": datasource.database,
        "username": datasource.username,
        "password_encrypted": datasource.password_encrypted,
    }
    if datasource.extra_config:
        config.update(datasource.extra_config)
    if datasource.type == "minio" and "secure" not in config:
        config["secure"] = bool(config.get("ssl", False))

    try:
        query_result = await execute_query(datasource.type, config, saved_sql.sql_text, limit)
        return query_result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
