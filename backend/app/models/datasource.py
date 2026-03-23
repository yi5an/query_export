from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class Datasource(Base):
    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    type = Column(String(50), nullable=False)  # postgres/clickhouse/redis 等
    host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=False)
    database = Column(String(100))
    username = Column(String(100))
    password_encrypted = Column(String)  # AES 加密存储
    extra_config = Column(JSON)  # 额外配置
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # 关系
    saved_sqls = relationship("SavedSql", back_populates="datasource")
    export_tasks = relationship("ExportTask", back_populates="datasource")