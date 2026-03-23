from pydantic import BaseModel
from typing import Optional, List


class SavedSqlBase(BaseModel):
    datasource_id: int
    name: str
    sql_text: str
    comment: Optional[str] = None
    tags: Optional[List[str]] = None


class SavedSqlCreate(SavedSqlBase):
    pass


class SavedSqlUpdate(BaseModel):
    name: Optional[str] = None
    sql_text: Optional[str] = None
    comment: Optional[str] = None
    tags: Optional[List[str]] = None


class SavedSql(SavedSqlBase):
    id: int
    run_count: int
    last_run_at: Optional[str] = None  # ISO format string
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True