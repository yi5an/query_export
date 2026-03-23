from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.api.deps import get_db_session
from app.schemas.datasource import DatasourceCreate, DatasourceUpdate, Datasource as DatasourceSchema
from app.models.datasource import Datasource as DatasourceModel
from app.core.security import encrypt_password, decrypt_password
from app.services.connector.factory import get_supported_types

router = APIRouter(tags=["数据源"])


def _encrypt_password_if_provided(data: dict) -> dict:
    """如果提供了密码则加密"""
    if data.get("password"):
        data["password_encrypted"] = encrypt_password(data.pop("password"))
    else:
        # 移除 password 字段，避免它被传递到模型
        data.pop("password", None)
    return data


@router.get("/", response_model=List[DatasourceSchema])
async def list_datasources(db: AsyncSession = Depends(get_db_session)):
    """获取数据源列表"""
    result = await db.execute(
        select(DatasourceModel).where(DatasourceModel.is_active == True)
    )
    datasources = result.scalars().all()
    return datasources


@router.get("/types")
async def list_supported_types():
    """获取后端实际支持的数据源类型"""
    return {"types": get_supported_types()}


@router.get("/{datasource_id}", response_model=DatasourceSchema)
async def get_datasource(datasource_id: int, db: AsyncSession = Depends(get_db_session)):
    """获取单个数据源"""
    result = await db.execute(
        select(DatasourceModel).where(
            DatasourceModel.id == datasource_id,
            DatasourceModel.is_active == True
        )
    )
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    return datasource


@router.post("/", response_model=DatasourceSchema)
async def create_datasource(
    datasource: DatasourceCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """创建数据源"""
    # 检查名称是否重复
    existing = await db.execute(
        select(DatasourceModel).where(DatasourceModel.name == datasource.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Datasource name already exists")

    # 加密密码
    data = datasource.model_dump()
    data = _encrypt_password_if_provided(data)

    db_datasource = DatasourceModel(**data)
    db.add(db_datasource)
    await db.commit()
    await db.refresh(db_datasource)
    return db_datasource


@router.put("/{datasource_id}", response_model=DatasourceSchema)
async def update_datasource(
    datasource_id: int,
    datasource: DatasourceUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """更新数据源"""
    result = await db.execute(
        select(DatasourceModel).where(DatasourceModel.id == datasource_id)
    )
    db_datasource = result.scalar_one_or_none()
    if not db_datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    # 检查名称是否与其他数据源重复
    if datasource.name:
        existing = await db.execute(
            select(DatasourceModel).where(
                DatasourceModel.name == datasource.name,
                DatasourceModel.id != datasource_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Datasource name already exists")

    # 更新字段
    update_data = datasource.model_dump(exclude_unset=True)
    update_data = _encrypt_password_if_provided(update_data)

    for field, value in update_data.items():
        setattr(db_datasource, field, value)

    await db.commit()
    await db.refresh(db_datasource)
    return db_datasource


@router.delete("/{datasource_id}")
async def delete_datasource(datasource_id: int, db: AsyncSession = Depends(get_db_session)):
    """删除数据源（软删除）"""
    result = await db.execute(
        select(DatasourceModel).where(DatasourceModel.id == datasource_id)
    )
    db_datasource = result.scalar_one_or_none()
    if not db_datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    db_datasource.is_active = False
    await db.commit()
    return {"message": "Datasource deleted"}


@router.post("/{datasource_id}/test")
async def test_datasource_connection(
    datasource_id: int,
    db: AsyncSession = Depends(get_db_session)
):
    """测试数据源连接"""
    result = await db.execute(
        select(DatasourceModel).where(DatasourceModel.id == datasource_id)
    )
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    try:
        from app.services.connector.factory import get_connector

        config = {
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": decrypt_password(datasource.password_encrypted) if datasource.password_encrypted else None,
        }
        if datasource.extra_config:
            config.update(datasource.extra_config)
        if datasource.type == "minio" and "secure" not in config:
            config["secure"] = bool(config.get("ssl", False))

        connector = get_connector(datasource.type, config)
        await connector.connect()
        is_connected = await connector.test_connection()
        await connector.close()

        if is_connected:
            return {"status": "success", "message": "Connection successful"}
        else:
            return {"status": "failed", "message": "Connection failed"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
