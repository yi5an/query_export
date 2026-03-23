from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.core.database import Base


class SavedSql(Base):
    __tablename__ = "saved_sqls"

    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id"))
    name = Column(String(200), nullable=False)
    sql_text = Column(Text, nullable=False)
    comment = Column(Text)  # 用于 AI 语义匹配
    tags = Column(ARRAY(String))  # 标签数组
    embedding = Column(Vector(1536))  # pgvector 向量存储
    run_count = Column(Integer, default=0)
    last_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    datasource = relationship("Datasource", back_populates="saved_sqls")
    export_tasks = relationship("ExportTask", back_populates="saved_sql")