from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class ExportTask(Base):
    __tablename__ = "export_tasks"

    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id"))
    saved_sql_id = Column(Integer, ForeignKey("saved_sqls.id"), nullable=True)
    sql_text = Column(Text, nullable=False)
    export_format = Column(String(20), nullable=False)  # csv/excel/sql/json
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    file_path = Column(Text)
    row_count = Column(Integer)  # 修复：使用 Integer 而非 BigInteger
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    # 关系
    datasource = relationship("Datasource", back_populates="export_tasks")
    saved_sql = relationship("SavedSql", back_populates="export_tasks")