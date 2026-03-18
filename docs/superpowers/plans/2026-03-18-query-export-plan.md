# QueryExport 实现计划

> **对于 AI 工作者**: 必须使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 来逐步执行此计划。步骤使用复选框 (`- [ ]`) 语法进行跟踪。

**目标**: 构建一个支持多数据源的 SQL 查询与导出工具，支持 AI 辅助生成 SQL

**架构**: Python FastAPI 后端 + Vue 3 前端，使用 PostgreSQL 存储应用数据，Docker Compose 部署

**技术栈**: FastAPI, SQLAlchemy, Vue 3, Element Plus, CodeMirror, pgvector

---

## 阶段 1: 项目基础架构

### Task 1: 后端项目结构搭建

**文件:**
- 创建: `backend/app/__init__.py`
- 创建: `backend/app/core/__init__.py`
- 创建: `backend/app/core/config.py`
- 创建: `backend/app/core/security.py`
- 创建: `backend/app/core/database.py`
- 创建: `backend/requirements.txt`
- 创建: `backend/.env.example`
- 创建: `backend/Dockerfile`

- [ ] **Step 1: 创建 requirements.txt**

```txt
# backend/requirements.txt
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
cryptography>=42.0.0
python-dotenv>=1.0.0
aiofiles>=23.2.0

# 数据库驱动
pgvector>=0.2.0
psycopg2-binary>=2.9.9
clickhouse-connect>=0.6.0
mysql-connector-python>=8.0.0
redis>=5.0.0
elasticsearch>=8.12.0
minio>=7.2.0

# 导出处理
openpyxl>=3.1.0
xlsxwriter>=3.1.9

# AI 相关
httpx>=0.26.0

# SQL 处理
sqlparse>=0.4.0
```

- [ ] **Step 2: 创建配置模块**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    app_name: str = "QueryExport"
    app_secret_key: str = "change-me-in-production"
    database_url: str = "postgresql+asyncpg://user:pass@localhost/queryexport"
    export_dir: str = "/app/exports"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: 创建安全模块（密码加密）**

```python
# backend/app/core/security.py
from cryptography.fernet import Fernet
from backend.app.core.config import get_settings

_settings = get_settings()
_cipher = Fernet(_settings.app_secret_key.encode())


def encrypt_password(password: str) -> str:
    """加密密码"""
    return _cipher.encrypt(password.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """解密密码"""
    return _cipher.decrypt(encrypted.encode()).decode()
```

- [ ] **Step 4: 创建数据库模块**

```python
# backend/app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import get_settings

_settings = get_settings()
engine = create_async_engine(_settings.database_url, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 5: 创建 .env.example**

```bash
# backend/.env.example
APP_NAME=QueryExport
APP_SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=postgresql+asyncpg://queryexport:queryexport123@localhost:5432/queryexport
EXPORT_DIR=/app/exports
```

- [ ] **Step 6: 创建 Dockerfile**

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 7: 提交**

```bash
git add backend/
git commit -m "feat: add backend core infrastructure"
```

---

### Task 2: 数据模型定义

**文件:**
- 创建: `backend/app/models/__init__.py`
- 创建: `backend/app/models/datasource.py`
- 创建: `backend/app/models/saved_sql.py`
- 创建: `backend/app/models/export_task.py`
- 创建: `backend/app/models/ai_config.py`
- 创建: `backend/app/schemas/__init__.py`
- 创建: `backend/app/schemas/datasource.py`

- [ ] **Step 1: 创建数据源模型**

```python
# backend/app/models/datasource.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from backend.app.core.database import Base


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
```

- [ ] **Step 2: 创建保存的 SQL 模型**

```python
# backend/app/models/saved_sql.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Array
from sqlalchemy.sql import func
from sqlalchemy import ForeignKey
from pgvector.sqlalchemy import Vector
from backend.app.core.database import Base


class SavedSql(Base):
    __tablename__ = "saved_sqls"

    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id"))
    name = Column(String(200), nullable=False)
    sql_text = Column(Text, nullable=False)
    comment = Column(Text)  # 用于 AI 语义匹配
    tags = Column(Array(String))  # 标签数组
    embedding = Column(Vector(1536))  # pgvector 向量存储
    run_count = Column(Integer, default=0)
    last_run_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 3: 创建导出任务模型**

```python
# backend/app/models/export_task.py
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, ForeignKey
from sqlalchemy.sql import func
from backend.app.core.database import Base


class ExportTask(Base):
    __tablename__ = "export_tasks"

    id = Column(Integer, primary_key=True, index=True)
    datasource_id = Column(Integer, ForeignKey("datasources.id"))
    saved_sql_id = Column(Integer, ForeignKey("saved_sqls.id"), nullable=True)
    sql_text = Column(Text, nullable=False)
    export_format = Column(String(20), nullable=False)  # csv/excel/sql/json
    status = Column(String(20), default="pending")  # pending/running/completed/failed
    file_path = Column(Text)
    row_count = Column(Integer)
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
```

- [ ] **Step 4: 创建 AI 配置模型**

```python
# backend/app/models/ai_config.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from backend.app.core.database import Base


class AiConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)  # openai/claude/ollama
    api_key_encrypted = Column(Text)
    base_url = Column(String(255))
    model_name = Column(String(100))
    extra_params = Column(JSON)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

- [ ] **Step 5: 创建 Pydantic Schema**

```python
# backend/app/schemas/datasource.py
from pydantic import BaseModel
from typing import Optional, Dict


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


class Datasource(DatasourceBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
```

- [ ] **Step 6: 提交**

```bash
git add backend/app/models/ backend/app/schemas/
git commit -m "feat: add database models and schemas"
```

---

### Task 3: 数据库迁移配置

**文件:**
- 创建: `backend/alembic.ini`
- 创建: `backend/alembic/env.py`
- 创建: `backend/alembic/versions/001_initial_migration.py`

- [ ] **Step 1: 初始化 Alembic**

```bash
cd backend
alembic init alembic
```

- [ ] **Step 2: 配置 alembic/env.py**

编辑 `backend/alembic/env.py`，添加:

```python
from backend.app.core.database import Base
from backend.app.models import datasource, saved_sql, export_task, ai_config

target_metadata = Base.metadata
```

- [ ] **Step 3: 创建初始迁移**

```bash
alembic revision --autogenerate -m "Initial migration"
```

- [ ] **Step 4: 编辑迁移文件，添加 pgvector 支持**

编辑 `backend/alembic/versions/001_initial_migration.py`:

```python
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


def upgrade():
    # 创建 pgvector 扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # 创建数据源表
    op.create_table(
        'datasources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('database', sa.String(length=100), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('password_encrypted', sa.String(), nullable=True),
        sa.Column('extra_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_datasources_id'), 'datasources', ['id'], unique=False)
    op.create_index(op.f('ix_datasources_name'), 'datasources', ['name'], unique=True)

    # 创建保存的 SQL 表，包含 embedding 列
    op.create_table(
        'saved_sqls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('datasource_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['datasource_id'], ['datasources.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_sqls_id'), 'saved_sqls', ['id'], unique=False)
    # 创建向量索引
    op.execute('CREATE INDEX ix_saved_sqls_embedding ON saved_sqls USING ivfflat (embedding vector_cosine_ops)')

    # 创建导出任务表
    op.create_table(
        'export_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('datasource_id', sa.Integer(), nullable=True),
        sa.Column('saved_sql_id', sa.Integer(), nullable=True),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('export_format', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['datasource_id'], ['datasources.id']),
        sa.ForeignKeyConstraint(['saved_sql_id'], ['saved_sqls.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_export_tasks_id'), 'export_tasks', ['id'], unique=False)

    # 创建 AI 配置表
    op.create_table(
        'ai_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(length=255), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('extra_params', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_configs_id'), 'ai_configs', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_ai_configs_id'), table_name='ai_configs')
    op.drop_table('ai_configs')
    op.drop_index(op.f('ix_export_tasks_id'), table_name='export_tasks')
    op.drop_table('export_tasks')
    op.execute('DROP INDEX IF EXISTS ix_saved_sqls_embedding')
    op.drop_index(op.f('ix_saved_sqls_id'), table_name='saved_sqls')
    op.drop_table('saved_sqls')
    op.drop_index(op.f('ix_datasources_name'), table_name='datasources')
    op.drop_index(op.f('ix_datasources_id'), table_name='datasources')
    op.drop_table('datasources')
    op.execute('DROP EXTENSION IF EXISTS vector')
```

- [ ] **Step 5: 提交**

```bash
git add backend/alembic/
git commit -m "feat: add database migration configuration"
```

---

### Task 4: Docker Compose 配置

**文件:**
- 创建: `docker-compose.yml`
- 创建: `docker-compose.dev.yml`
- 创建: `.env.example`

- [ ] **Step 1: 创建 docker-compose.yml**

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    container_name: queryexport-db
    environment:
      POSTGRES_USER: ${DB_USER:-queryexport}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-queryexport123}
      POSTGRES_DB: ${DB_NAME:-queryexport}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${DB_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-queryexport}"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: queryexport-backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER:-queryexport}:${DB_PASSWORD:-queryexport123}@postgres:5432/${DB_NAME:-queryexport}
      - APP_SECRET_KEY=${APP_SECRET_KEY:-your-secret-key}
      - EXPORT_DIR=/app/exports
    volumes:
      - ./backend/app:/app/app
      - ./exports:/app/exports
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    depends_on:
      postgres:
        condition: service_healthy
    command: sh -c "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

volumes:
  postgres_data:
```

- [ ] **Step 2: 创建 .env.example**

```bash
# .env.example
# 数据库配置
DB_USER=queryexport
DB_PASSWORD=queryexport123
DB_NAME=queryexport
DB_PORT=5432

# 应用配置
APP_SECRET_KEY=your-secret-key-change-in-production

# 端口配置
BACKEND_PORT=8000
FRONTEND_PORT=80
```

- [ ] **Step 3: 提交**

```bash
git add docker-compose.yml .env.example
git commit -m "feat: add docker compose configuration"
```

---

### Task 5: FastAPI 主应用入口

**文件:**
- 创建: `backend/app/main.py`
- 创建: `backend/app/api/__init__.py`
- 创建: `backend/app/api/v1/__init__.py`
- 创建: `backend/app/api/v1/datasources.py`
- 创建: `backend/app/api/v1/health.py`
- 创建: `backend/app/api/deps.py`

- [ ] **Step 1: 创建依赖注入模块**

```python
# backend/app/api/deps.py
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.database import AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 2: 创建健康检查 API**

```python
# backend/app/api/v1/health.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: str
    message: str


@router.get("/", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="ok", message="QueryExport API is running")
```

- [ ] **Step 3: 创建数据源 API（基础框架）**

```python
# backend/app/api/v1/datasources.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from backend.app.api.deps import get_db
from backend.app.schemas.datasource import DatasourceCreate, Datasource as DatasourceSchema

router = APIRouter(prefix="/datasources", tags=["datasources"])


@router.get("/", response_model=List[DatasourceSchema])
async def list_datasources(db: AsyncSession = Depends(get_db)):
    """获取数据源列表"""
    # TODO: 实现查询逻辑
    return []


@router.post("/", response_model=DatasourceSchema)
async def create_datasource(
    datasource: DatasourceCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建数据源"""
    # TODO: 实现创建逻辑
    raise HTTPException(status_code=501, detail="Not implemented yet")
```

- [ ] **Step 4: 创建主应用入口**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.v1 import health, datasources

app = FastAPI(
    title="QueryExport",
    description="SQL 导出工具 API",
    version="1.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, prefix="/api/v1")
app.include_router(datasources.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"message": "QueryExport API", "docs": "/docs"}
```

- [ ] **Step 5: 测试启动**

```bash
docker-compose up -d --build
docker-compose logs -f backend
```

访问 http://localhost:8000/docs 验证 API 文档

- [ ] **Step 6: 提交**

```bash
git add backend/app/
git commit -m "feat: add FastAPI main application and API routes"
```

---

## 阶段 2: 数据源连接器

### Task 6: 连接器基类和 PostgreSQL 实现

**文件:**
- 创建: `backend/app/services/connector/__init__.py`
- 创建: `backend/app/services/connector/base.py`
- 创建: `backend/app/services/connector/postgres.py`
- 创建: `backend/app/services/connector/factory.py`

- [ ] **Step 1: 创建连接器基类**

```python
# backend/app/services/connector/base.py
from abc import ABC, abstractmethod
from typing import AsyncIterator, Any, Dict, List


class BaseConnector(ABC):
    """数据源连接器抽象基类"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._connection = None

    @abstractmethod
    async def connect(self) -> None:
        """建立连接"""
        pass

    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """测试连接"""
        pass

    @abstractmethod
    async def execute(self, sql: str, limit: int = None) -> Dict[str, Any]:
        """
        执行查询
        返回: {
            "columns": ["col1", "col2"],
            "rows": [[1, "a"], [2, "b"]],
            "row_count": 2
        }
        """
        pass

    @abstractmethod
    async def stream_execute(self, sql: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        """流式执行，用于大数据导出"""
        pass

    @abstractmethod
    def get_export_formats(self) -> List[str]:
        """返回该数据源支持的导出格式"""
        pass

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
```

- [ ] **Step 2: 实现 PostgreSQL 连接器**

```python
# backend/app/services/connector/postgres.py
import asyncpg
from typing import AsyncIterator, Any, Dict, List
from backend.app.services.connector.base import BaseConnector


class PostgresConnector(BaseConnector):
    """PostgreSQL 连接器"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._pool = None

    async def connect(self) -> None:
        """建立连接池"""
        self._pool = await asyncpg.create_pool(
            host=self.config.get('host'),
            port=self.config.get('port', 5432),
            database=self.config.get('database'),
            user=self.config.get('username'),
            password=self.config.get('password'),
            min_size=1,
            max_size=5
        )

    async def close(self) -> None:
        """关闭连接池"""
        if self._pool:
            await self._pool.close()

    async def test_connection(self) -> bool:
        """测试连接"""
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False

    async def execute(self, sql: str, limit: int = None) -> Dict[str, Any]:
        """执行查询"""
        if limit:
            sql = f"{sql} LIMIT {limit}"

        async with self._pool.acquire() as conn:
            asyncpg_conn = conn
            rows = await asyncpg_conn.fetch(sql)
            if rows:
                columns = list(rows[0].keys())
                row_data = [list(row.values()) for row in rows]
            else:
                columns = []
                row_data = []

            return {
                "columns": columns,
                "rows": row_data,
                "row_count": len(row_data)
            }

    async def stream_execute(self, sql: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]:
        """流式执行"""
        async with self._pool.acquire() as conn:
            asyncpg_conn = conn
            async for batch in asyncpg_conn.cursor(sql).fetch(batch_size):
                yield [list(row.values()) for row in batch]

    def get_export_formats(self) -> List[str]:
        """支持的导出格式"""
        return ["csv", "excel", "sql"]
```

- [ ] **Step 3: 创建连接器工厂**

```python
# backend/app/services/connector/factory.py
from typing import Dict, Any
from backend.app.services.connector.base import BaseConnector
from backend.app.services.connector.postgres import PostgresConnector

CONNECTOR_REGISTRY = {
    'postgres': PostgresConnector,
}


def get_connector(datasource_type: str, config: Dict[str, Any]) -> BaseConnector:
    """根据数据源类型获取连接器实例"""
    connector_class = CONNECTOR_REGISTRY.get(datasource_type)
    if not connector_class:
        raise ValueError(f"Unsupported datasource type: {datasource_type}")
    return connector_class(config)
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/connector/
git commit -m "feat: add connector base class and PostgreSQL implementation"
```

---

### Task 7: 数据源管理 API 实现

**文件:**
- 修改: `backend/app/api/v1/datasources.py`

- [ ] **Step 1: 实现数据源 CRUD**

```python
# backend/app/api/v1/datasources.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from backend.app.api.deps import get_db
from backend.app.schemas.datasource import DatasourceCreate, DatasourceUpdate, Datasource as DatasourceSchema
from backend.app.models.datasource import Datasource as DatasourceModel
from backend.app.core.security import encrypt_password, decrypt_password

router = APIRouter(prefix="/datasources", tags=["datasources"])


def _encrypt_password_if_provided(data: dict) -> dict:
    """如果提供了密码则加密"""
    if data.get("password"):
        data["password_encrypted"] = encrypt_password(data.pop("password"))
    return data


@router.get("/", response_model=List[DatasourceSchema])
async def list_datasources(db: AsyncSession = Depends(get_db)):
    """获取数据源列表"""
    result = await db.execute(select(DatasourceModel).where(DatasourceModel.is_active == True))
    datasources = result.scalars().all()
    return datasources


@router.get("/{datasource_id}", response_model=DatasourceSchema)
async def get_datasource(datasource_id: int, db: AsyncSession = Depends(get_db)):
    """获取单个数据源"""
    result = await db.execute(select(DatasourceModel).where(DatasourceModel.id == datasource_id))
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")
    return datasource


@router.post("/", response_model=DatasourceSchema)
async def create_datasource(
    datasource: DatasourceCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建数据源"""
    # 检查名称是否重复
    existing = await db.execute(
        select(DatasourceModel).where(DatasourceModel.name == datasource.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Datasource name already exists")

    # 加密密码
    data = datasource.dict()
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
    db: AsyncSession = Depends(get_db)
):
    """更新数据源"""
    result = await db.execute(select(DatasourceModel).where(DatasourceModel.id == datasource_id))
    db_datasource = result.scalar_one_or_none()
    if not db_datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    # 更新字段
    update_data = datasource.dict(exclude_unset=True)
    update_data = _encrypt_password_if_provided(update_data)

    for field, value in update_data.items():
        setattr(db_datasource, field, value)

    await db.commit()
    await db.refresh(db_datasource)
    return db_datasource


@router.delete("/{datasource_id}")
async def delete_datasource(datasource_id: int, db: AsyncSession = Depends(get_db)):
    """删除数据源（软删除）"""
    result = await db.execute(select(DatasourceModel).where(DatasourceModel.id == datasource_id))
    db_datasource = result.scalar_one_or_none()
    if not db_datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    db_datasource.is_active = False
    await db.commit()
    return {"message": "Datasource deleted"}


@router.post("/{datasource_id}/test")
async def test_datasource_connection(datasource_id: int, db: AsyncSession = Depends(get_db)):
    """测试数据源连接"""
    result = await db.execute(select(DatasourceModel).where(DatasourceModel.id == datasource_id))
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    try:
        from backend.app.services.connector.factory import get_connector

        config = {
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password": decrypt_password(datasource.password_encrypted) if datasource.password_encrypted else None,
        }

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
```

- [ ] **Step 2: 更新 Schema 支持密码不返回**

```python
# backend/app/schemas/datasource.py (更新)
class Datasource(DatasourceBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
        # 密码不返回给前端
        fields = {'password': {'exclude': True}}
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/api/v1/datasources.py backend/app/schemas/datasource.py
git commit -m "feat: implement datasource CRUD operations"
```

---

## 阶段 3: 查询执行功能

### Task 8: 查询服务实现

**文件:**
- 创建: `backend/app/services/query.py`
- 创建: `backend/app/api/v1/queries.py`

- [ ] **Step 1: 创建查询服务**

```python
# backend/app/services/query.py
from typing import Dict, Any
from backend.app.services.connector.factory import get_connector
from backend.app.core.security import decrypt_password


async def execute_query(
    datasource_type: str,
    config: Dict[str, Any],
    sql: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    执行查询
    config 包含 host, port, database, username, password_encrypted 等
    """
    # 解密密码
    if "password_encrypted" in config:
        config["password"] = decrypt_password(config["password_encrypted"])
        del config["password_encrypted"]

    connector = get_connector(datasource_type, config)
    await connector.connect()

    try:
        result = await connector.execute(sql, limit=limit)
        return result
    finally:
        await connector.close()
```

- [ ] **Step 2: 创建查询 API**

```python
# backend/app/api/v1/queries.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from backend.app.api.deps import get_db
from backend.app.models.datasource import Datasource as DatasourceModel
from backend.app.services.query import execute_query

router = APIRouter(prefix="/query", tags=["queries"])


class QueryRequest(BaseModel):
    datasource_id: int
    sql: str
    limit: Optional[int] = 10


class QueryResponse(BaseModel):
    columns: list
    rows: list
    row_count: int
    execution_time_ms: Optional[float] = None


@router.post("/execute", response_model=QueryResponse)
async def execute_query_api(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """执行 SQL 查询（试运行，默认返回 10 行）"""
    # 获取数据源配置
    result = await db.execute(
        select(DatasourceModel).where(DatasourceModel.id == request.datasource_id)
    )
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    # 准备配置
    config = {
        "host": datasource.host,
        "port": datasource.port,
        "database": datasource.database,
        "username": datasource.username,
        "password_encrypted": datasource.password_encrypted,
    }
    if datasource.extra_config:
        config.update(datasource.extra_config)

    # 执行查询
    import time
    start_time = time.time()

    try:
        query_result = await execute_query(
            datasource.type,
            config,
            request.sql,
            request.limit
        )

        execution_time = (time.time() - start_time) * 1000

        # 更新 SQL 运行次数（如果是保存的 SQL）
        # TODO: 后续实现

        return QueryResponse(
            columns=query_result["columns"],
            rows=query_result["rows"],
            row_count=query_result["row_count"],
            execution_time_ms=execution_time
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


class FormatRequest(BaseModel):
    sql: str
    dialect: Optional[str] = "postgres"


@router.post("/format")
async def format_sql(request: FormatRequest):
    """格式化 SQL"""
    import sqlparse
    formatted = sqlparse.format(
        request.sql,
        reindent=True,
        keyword_case='upper'
    )
    return {"formatted_sql": formatted}


class ValidateRequest(BaseModel):
    datasource_id: int
    sql: str


class ValidateResponse(BaseModel):
    is_valid: bool
    error: Optional[str] = None


@router.post("/validate", response_model=ValidateResponse)
async def validate_sql(request: ValidateRequest, db: AsyncSession = Depends(get_db)):
    """验证 SQL 语法"""
    # 获取数据源
    result = await db.execute(
        select(DatasourceModel).where(DatasourceModel.id == request.datasource_id)
    )
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    # 基本语法检查（根据不同数据源类型）
    try:
        import sqlparse
        parsed = sqlparse.parse(request.sql)

        if not parsed or not parsed[0]:
            return ValidateResponse(is_valid=False, error="Empty SQL")

        # 基本检查：是否包含 SELECT/INSERT/UPDATE/DELETE 等关键词
        sql_upper = request.sql.upper().strip()
        if not any(kw in sql_upper for kw in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'DROP', 'ALTER', 'SHOW', 'DESC', 'DESCRIBE']):
            return ValidateResponse(is_valid=False, error="No valid SQL keyword found")

        return ValidateResponse(is_valid=True)

    except Exception as e:
        return ValidateResponse(is_valid=False, error=str(e))
```

- [ ] **Step 3: 注册路由**

更新 `backend/app/main.py`:

```python
from backend.app.api.v1 import queries

app.include_router(queries.router, prefix="/api/v1")
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/query.py backend/app/api/v1/queries.py backend/app/main.py
git commit -m "feat: add query execution API"
```

---

## 阶段 4: 前端开发

### Task 9: 前端项目初始化

**文件:**
- 创建: `frontend/package.json`
- 创建: `frontend/vite.config.ts`
- 创建: `frontend/tsconfig.json`
- 创建: `frontend/index.html`
- 创建: `frontend/src/main.ts`
- 创建: `frontend/src/App.vue`
- 创建: `frontend/Dockerfile`
- 创建: `frontend/nginx.conf`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "query-export-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "element-plus": "^2.5.0",
    "@element-plus/icons-vue": "^2.3.0",
    "sql-formatter": "^15.0.0",
    "vue-virtual-scroller": "^2.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.3.0",
    "vue-tsc": "^1.8.0",
    "vite": "^5.0.0"
  }
}
```

- [ ] **Step 2: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: 创建 tsconfig.json**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "preserve",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"]
    }
  },
  "include": ["src/**/*.ts", "src/**/*.d.ts", "src/**/*.tsx", "src/**/*.vue"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
```

- [ ] **Step 4: 创建主应用文件**

```html
<!-- frontend/index.html -->
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>QueryExport</title>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

```typescript
// frontend/src/main.ts
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.use(ElementPlus)
app.mount('#app')
```

```vue
<!-- frontend/src/App.vue -->
<template>
  <div id="app">
    <router-view />
  </div>
</template>

<script setup lang="ts">
</script>

<style>
#app {
  height: 100vh;
  margin: 0;
  padding: 0;
}
</style>
```

- [ ] **Step 5: 创建路由**

```typescript
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'QueryEditor',
      component: () => import('@/views/QueryEditor.vue')
    }
  ]
})

export default router
```

- [ ] **Step 6: 更新 main.ts 添加路由**

```typescript
import router from './router'
app.use(router)
```

- [ ] **Step 7: 创建 Dockerfile**

```dockerfile
# 构建阶段
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# 生产阶段
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 8: 创建 nginx.conf**

```nginx
server {
    listen 80;

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

- [ ] **Step 9: 创建 frontend/.env.example**

```bash
# frontend/.env.example
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

- [ ] **Step 10: 提交**

```bash
git add frontend/
git commit -m "feat: add frontend project structure"
```

---

### Task 11: SQL 编辑器组件

**文件:**
- 创建: `frontend/src/components/SqlEditor.vue`
- 创建: `frontend/src/views/QueryEditor.vue`
- 更新: `frontend/package.json` (添加 CodeMirror)

- [ ] **Step 1: 添加 CodeMirror 依赖**

更新 `frontend/package.json`:

```json
{
  "dependencies": {
    "@codemirror/lang-sql": "^6.6.0",
    "@codemirror/theme-one-dark": "^6.1.0",
    "codemirror": "^6.0.0",
    "vue-codemirror": "^6.1.1"
  }
}
```

- [ ] **Step 2: 创建 SQL 编辑器组件**

```vue
<!-- frontend/src/components/SqlEditor.vue -->
<template>
  <div class="sql-editor">
    <codemirror
      v-model="code"
      :style="{ height: height }"
      :extensions="extensions"
      @ready="handleReady"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Codemirror } from 'vue-codemirror'
import { sql } from '@codemirror/lang-sql'
import { oneDark } from '@codemirror/theme-one-dark'
import type { ViewUpdate } from '@codemirror/view'

interface Props {
  modelValue: string
  height?: string
  theme?: 'light' | 'dark'
}

const props = withDefaults(defineProps<Props>(), {
  height: '300px',
  theme: 'light'
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const code = computed({
  get: () => props.modelValue,
  set: (value: string) => emit('update:modelValue', value)
})

const extensions = computed(() => {
  const exts = [sql()]
  if (props.theme === 'dark') {
    exts.push(oneDark)
  }
  return exts
})

const handleReady = (payload: { view: any; state: any; container: HTMLDivElement }) => {
  // 编辑器准备就绪
  console.log('SQL Editor ready')
}
</script>

<style scoped>
.sql-editor {
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  overflow: hidden;
}

:deep(.cm-editor) {
  height: 100%;
}

:deep(.cm-scroller) {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 14px;
}
</style>
```

- [ ] **Step 3: 创建查询编辑器页面**

```vue
<!-- frontend/src/views/QueryEditor.vue -->
<template>
  <div class="query-editor-page">
    <el-container>
      <el-header>
        <div class="header-content">
          <h1>QueryExport</h1>
          <el-select v-model="selectedDatasourceId" placeholder="选择数据源" style="width: 200px">
            <el-option
              v-for="ds in datasources"
              :key="ds.id"
              :label="ds.name"
              :value="ds.id"
            />
          </el-select>
        </div>
      </el-header>

      <el-main>
        <div class="editor-section">
          <div class="toolbar">
            <el-button type="primary" @click="executeQuery" :loading="executing">
              试运行
            </el-button>
            <el-button @click="formatSQL">格式化</el-button>
            <el-button @click="saveSQL">保存 SQL</el-button>
            <el-button @click="showExportDialog = true">导出</el-button>
          </div>

          <SqlEditor
            v-model="sql"
            :height="'400px'"
            @update:modelValue="onSQLChange"
          />
        </div>

        <div class="result-section" v-if="queryResult">
          <div class="result-header">
            <span>执行结果</span>
            <span class="meta">
              耗时: {{ queryResult.execution_time_ms?.toFixed(2) }}ms |
              行数: {{ queryResult.row_count }}
            </span>
          </div>
          <el-table
            :data="queryResult.rows"
            :border="true"
            stripe
            max-height="400"
          >
            <el-table-column
              v-for="(col, index) in queryResult.columns"
              :key="index"
              :prop="index.toString()"
              :label="col"
            />
          </el-table>
        </div>
      </el-main>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import SqlEditor from '@/components/SqlEditor.vue'
import api from '@/api'

const selectedDatasourceId = ref<number>()
const datasources = ref<any[]>([])
const sql = ref('SELECT * FROM users LIMIT 10;')
const executing = ref(false)
const queryResult = ref<any>(null)
const showExportDialog = ref(false)

onMounted(async () => {
  await loadDatasources()
})

async function loadDatasources() {
  try {
    const response = await api.get('/api/v1/datasources')
    datasources.value = response.data
  } catch (error) {
    ElMessage.error('加载数据源失败')
  }
}

async function executeQuery() {
  if (!selectedDatasourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }

  executing.value = true
  try {
    const response = await api.post('/api/v1/query/execute', {
      datasource_id: selectedDatasourceId.value,
      sql: sql.value,
      limit: 10
    })
    queryResult.value = response.data
    ElMessage.success('查询成功')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '查询失败')
  } finally {
    executing.value = false
  }
}

async function formatSQL() {
  try {
    const response = await api.post('/api/v1/query/format', {
      sql: sql.value
    })
    sql.value = response.data.formatted_sql
  } catch (error) {
    ElMessage.error('格式化失败')
  }
}

function saveSQL() {
  ElMessage.info('保存功能开发中...')
}

function onSQLChange(value: string) {
  // SQL 变化时的处理
}
</script>

<style scoped>
.query-editor-page {
  height: 100vh;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 20px;
}

.editor-section {
  margin-bottom: 20px;
}

.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 10px;
}

.result-section {
  background: white;
  border-radius: 4px;
  padding: 16px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-weight: bold;
}

.meta {
  color: #909399;
  font-weight: normal;
}
</style>
```

- [ ] **Step 4: 创建 API 模块**

```typescript
// frontend/src/api/index.ts
import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  timeout: 30000
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data
  },
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default api
```

- [ ] **Step 5: 更新 docker-compose.yml 添加前端**

```yaml
  frontend:
    build: ./frontend
    container_name: queryexport-frontend
    ports:
      - "${FRONTEND_PORT:-80}:80"
    depends_on:
      - backend
```

- [ ] **Step 6: 提交**

```bash
git add frontend/
git commit -m "feat: add SQL editor and query page"
```

---

## 阶段 5: 导出功能

### Task 12: 导出处理器实现

**文件:**
- 创建: `backend/app/services/export/csv_handler.py`
- 创建: `backend/app/services/export/excel_handler.py`
- 创建: `backend/app/services/export/__init__.py`

- [ ] **Step 1: 创建 CSV 导出处理器**

```python
# backend/app/services/export/csv_handler.py
import csv
import io
from typing import List, Any
from pathlib import Path


class CSVHandler:
    """CSV 导出处理器"""

    @staticmethod
    async def write(
        columns: List[str],
        rows: List[List[Any]],
        output_path: str
    ) -> int:
        """
        写入 CSV 文件
        返回写入的行数
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            writer.writerows(rows)

        return len(rows)

    @staticmethod
    def get_content_type() -> str:
        return "text/csv"

    @staticmethod
    def get_extension() -> str:
        return ".csv"
```

- [ ] **Step 2: 创建 Excel 导出处理器**

```python
# backend/app/services/export/excel_handler.py
import xlsxwriter
from typing import List, Any
from pathlib import Path


class ExcelHandler:
    """Excel 导出处理器"""

    @staticmethod
    async def write(
        columns: List[str],
        rows: List[List[Any]],
        output_path: str
    ) -> int:
        """
        写入 Excel 文件
        返回写入的行数
        """
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        workbook = xlsxwriter.Workbook(output_path, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # 写入表头
        for col_idx, col_name in enumerate(columns):
            worksheet.write(0, col_idx, col_name)

        # 写入数据
        for row_idx, row in enumerate(rows, start=1):
            for col_idx, value in enumerate(row):
                worksheet.write(row_idx, col_idx, value)

        workbook.close()
        return len(rows)

    @staticmethod
    def get_content_type() -> str:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @staticmethod
    def get_extension() -> str:
        return ".xlsx"
```

- [ ] **Step 3: 提交**

```bash
git add backend/app/services/export/
git commit -m "feat: add CSV and Excel export handlers"
```

---

### Task 13: 导出 API 实现

**文件:**
- 创建: `backend/app/api/v1/exports.py`
- 创建: `backend/app/services/export.py`

- [ ] **Step 1: 创建导出服务**

```python
# backend/app/services/export.py
import uuid
from pathlib import Path
from typing import List, Any, AsyncIterator
from backend.app.services.connector.factory import get_connector
from backend.app.services.export.csv_handler import CSVHandler
from backend.app.services.export.excel_handler import ExcelHandler
from backend.app.core.security import decrypt_password

EXPORT_HANDLERS = {
    "csv": CSVHandler,
    "excel": ExcelHandler,
}


async def export_data(
    datasource_type: str,
    config: dict,
    sql: str,
    export_format: str,
    export_dir: str
) -> tuple[str, int]:
    """
    执行导出
    返回 (文件路径, 行数)
    """
    # 解密密码
    if "password_encrypted" in config:
        config["password"] = decrypt_password(config["password_encrypted"])
        del config["password_encrypted"]

    # 获取处理器
    handler_class = EXPORT_HANDLERS.get(export_format)
    if not handler_class:
        raise ValueError(f"Unsupported export format: {export_format}")

    handler = handler_class()

    # 连接数据源
    connector = get_connector(datasource_type, config)
    await connector.connect()

    try:
        # 获取列名
        result = await connector.execute(sql, limit=1)
        columns = result["columns"]

        # 流式导出
        file_name = f"{uuid.uuid4()}{handler.get_extension()}"
        output_path = str(Path(export_dir) / file_name)

        # 收集所有行（简化版本，大数据量应该用流式处理）
        all_rows = []
        async for batch in connector.stream_execute(sql, batch_size=1000):
            all_rows.extend(batch)

        # 写入文件
        row_count = await handler.write(columns, all_rows, output_path)

        return output_path, row_count

    finally:
        await connector.close()
```

- [ ] **Step 2: 创建导出 API**

```python
# backend/app/api/v1/exports.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
from backend.app.api.deps import get_db
from backend.app.models.datasource import Datasource as DatasourceModel
from backend.app.models.export_task import ExportTask as ExportTaskModel
from backend.app.services.export import export_data
from backend.app.core.config import get_settings

router = APIRouter(prefix="/exports", tags=["exports"])
_settings = get_settings()


class ExportRequest(BaseModel):
    datasource_id: int
    sql: str
    format: str  # csv/excel/sql/json


class ExportResponse(BaseModel):
    task_id: int
    status: str
    message: str


@router.post("/", response_model=ExportResponse)
async def create_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """创建导出任务"""
    # 获取数据源
    result = await db.execute(
        select(DatasourceModel).where(DatasourceModel.id == request.datasource_id)
    )
    datasource = result.scalar_one_or_none()
    if not datasource:
        raise HTTPException(status_code=404, detail="Datasource not found")

    # 创建任务记录
    task = ExportTaskModel(
        datasource_id=request.datasource_id,
        sql_text=request.sql,
        export_format=request.format,
        status="pending"
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 后台执行导出
    background_tasks.add_task(
        _execute_export,
        task.id,
        datasource,
        request.sql,
        request.format,
        db
    )

    return ExportResponse(
        task_id=task.id,
        status="pending",
        message="Export task created"
    )


async def _execute_export(
    task_id: int,
    datasource: DatasourceModel,
    sql: str,
    export_format: str,
    db: AsyncSession
):
    """后台执行导出"""
    from sqlalchemy import update

    # 更新状态为运行中
    await db.execute(
        update(ExportTaskModel)
        .where(ExportTaskModel.id == task_id)
        .values(status="running")
    )
    await db.commit()

    try:
        # 准备配置
        config = {
            "host": datasource.host,
            "port": datasource.port,
            "database": datasource.database,
            "username": datasource.username,
            "password_encrypted": datasource.password_encrypted,
        }
        if datasource.extra_config:
            config.update(datasource.extra_config)

        # 执行导出
        file_path, row_count = await export_data(
            datasource.type,
            config,
            sql,
            export_format,
            _settings.export_dir
        )

        # 更新状态为完成
        await db.execute(
            update(ExportTaskModel)
            .where(ExportTaskModel.id == task_id)
            .values(
                status="completed",
                file_path=file_path,
                row_count=row_count
            )
        )
        await db.commit()

    except Exception as e:
        # 更新状态为失败
        await db.execute(
            update(ExportTaskModel)
            .where(ExportTaskModel.id == task_id)
            .values(
                status="failed",
                error_message=str(e)
            )
        )
        await db.commit()


@router.get("/")
async def list_exports(db: AsyncSession = Depends(get_db)):
    """获取导出任务列表"""
    result = await db.execute(select(ExportTaskModel).order_by(ExportTaskModel.created_at.desc()))
    tasks = result.scalars().all()
    return tasks


@router.get("/{task_id}")
async def get_export(task_id: int, db: AsyncSession = Depends(get_db)):
    """获取导出任务详情"""
    result = await db.execute(select(ExportTaskModel).where(ExportTaskModel.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/{task_id}/download")
async def download_export(task_id: int, db: AsyncSession = Depends(get_db)):
    """下载导出文件"""
    result = await db.execute(select(ExportTaskModel).where(ExportTaskModel.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail="Export not completed")

    file_path = Path(task.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=str(file_path),
        filename=file_path.name,
        media_type="application/octet-stream"
    )


@router.delete("/{task_id}")
async def delete_export(task_id: int, db: AsyncSession = Depends(get_db)):
    """删除导出任务"""
    result = await db.execute(select(ExportTaskModel).where(ExportTaskModel.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 删除文件
    if task.file_path:
        file_path = Path(task.file_path)
        if file_path.exists():
            file_path.unlink()

    # 删除记录
    await db.delete(task)
    await db.commit()

    return {"message": "Task deleted"}
```

- [ ] **Step 3: 注册路由**

更新 `backend/app/main.py`:

```python
from backend.app.api.v1 import exports

app.include_router(exports.router, prefix="/api/v1")
```

- [ ] **Step 4: 提交**

```bash
git add backend/app/services/export.py backend/app/api/v1/exports.py backend/app/main.py
git commit -m "feat: add export API with background tasks"
```

---

## 后续阶段（简要列出）

### 阶段 6: 更多数据源连接器
- ClickHouse 连接器
- Doris 连接器
- Redis 连接器
- Elasticsearch 连接器
- MinIO 连接器

### 阶段 7: SQL 保存管理
- 保存/加载 SQL API
- 前端 SQL 列表组件
- 标签管理

### 阶段 8: AI 功能
- AI Provider 抽象
- OpenAI/Claude/Ollama 实现
- 向量化与语义匹配
- AI 对话组件

### 阶段 9: 完善与优化
- 单元测试
- 错误处理
- 性能优化
- 文档完善

---

## 验证步骤

每完成一个 Task，运行以下命令验证：

```bash
# 1. 检查代码风格（如果有配置）
# black backend/
# pylint backend/

# 2. 运行测试（如果有）
# pytest backend/tests/

# 3. 构建 Docker 镜像
docker-compose build

# 4. 启动服务
docker-compose up -d

# 5. 查看日志
docker-compose logs -f

# 6. 访问 API 文档
# http://localhost:8000/docs
```

---

## 开发注意事项

1. **密码安全**: 始终使用加密存储密码，日志中不输出敏感信息
2. **SQL 注入**: 执行用户 SQL 前做基本验证，限制危险操作
3. **资源管理**: 使用 async context manager 确保连接正确关闭
4. **错误处理**: 提供清晰的错误信息，便于调试
5. **提交规范**: 使用约定式提交 `feat:`, `fix:`, `docs:` 等
