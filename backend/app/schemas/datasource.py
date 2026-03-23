from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict
from datetime import datetime


class DatasourceBase(BaseModel):
    name: str
    type: str
    host: str
    port: int
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    extra_config: Optional[Dict] = None


class DatasourceCreate(DatasourceBase):
    pass


class DatasourceUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    extra_config: Optional[Dict] = None
    is_active: Optional[bool] = None


class Datasource(BaseModel):
    """数据源响应 Schema - 不包含密码字段"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    host: str
    port: int
    database: Optional[str] = None
    username: Optional[str] = None
    extra_config: Optional[Dict] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None