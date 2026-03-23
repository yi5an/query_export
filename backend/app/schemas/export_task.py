from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


class ExportTaskBase(BaseModel):
    datasource_id: int
    sql_text: str
    export_format: str  # csv/excel/sql/json
    saved_sql_id: Optional[int] = None


class ExportTaskCreate(ExportTaskBase):
    pass


class ExportTask(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    datasource_id: int
    datasource_name: Optional[str] = None
    sql_text: str
    export_format: str
    status: str
    file_path: Optional[str] = None
    row_count: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    remaining_seconds: Optional[int] = None
