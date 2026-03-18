# QueryExport - SQL 导出工具设计文档

## 概述

QueryExport 是一个支持多数据源的 SQL 查询与导出工具，支持 AI 辅助生成 SQL，适用于小团队内部使用。

## 技术选型

| 层级 | 技术 |
|------|------|
| 后端框架 | Python FastAPI |
| 前端框架 | Vue 3 + Element Plus |
| SQL 编辑器 | CodeMirror 6 |
| 应用数据库 | PostgreSQL + pgvector |
| 部署方式 | Docker Compose |

## 功能需求

### 1. 多数据源支持

| 数据源 | 查询支持 | 导出格式 |
|--------|----------|----------|
| PostgreSQL | SQL | CSV, Excel, SQL |
| ClickHouse | SQL | CSV, Excel, SQL |
| Doris | SQL | CSV, Excel, SQL |
| Redis | 命令 | CSV, Excel |
| Redis-Cluster | 命令 | CSV, Excel |
| Elasticsearch | Query DSL | CSV, Excel, JSON |
| MinIO | - | 文件直接下载 |

### 2. 核心功能

- **SQL 执行与试运行**: 默认返回 10 行预览
- **SQL 格式化**: 编辑器内置格式化功能
- **SQL 保存与注释**: 保存常用 SQL，添加注释用于 AI 匹配
- **AI 生成 SQL**: 根据自然语言描述，语义匹配已保存 SQL 并生成新 SQL
- **数据导出**: 支持大数据量流式导出 + 异步任务模式

### 3. 非功能性需求

- 无用户认证（内网信任模式）
- 数据源密码 AES 加密存储
- 大数据量导出内存友好

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────┐
│                    Vue 前端                          │
│  (SQL编辑器 / 数据源管理 / 任务列表 / AI对话)         │
└─────────────────────────┬───────────────────────────┘
                          │ HTTP/WebSocket
┌─────────────────────────▼───────────────────────────┐
│                 FastAPI 后端                         │
├─────────────────────────────────────────────────────┤
│  api/          # 路由层                              │
│  services/     # 业务逻辑                            │
│    ├── connector/    # 数据源连接管理                 │
│    ├── query/        # 查询执行                      │
│    ├── export/       # 导出处理                      │
│    └── ai/           # AI SQL生成                   │
│  models/       # 数据模型                            │
│  core/         # 配置、工具                          │
└─────────────────────────┬───────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
   ┌─────────┐      ┌─────────┐      ┌─────────┐
   │PostgreSQL│      │ 目标数据源 │      │ AI API  │
   │(应用数据) │      │ (执行SQL)  │      │         │
   └─────────┘      └─────────┘      └─────────┘
```

### 项目结构

```
QueryExport/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── datasources.py
│   │   │   │   ├── queries.py
│   │   │   │   ├── exports.py
│   │   │   │   ├── saved_sql.py
│   │   │   │   └── ai.py
│   │   │   └── deps.py
│   │   ├── services/
│   │   │   ├── connector/
│   │   │   │   ├── base.py
│   │   │   │   ├── postgres.py
│   │   │   │   ├── clickhouse.py
│   │   │   │   ├── doris.py
│   │   │   │   ├── redis.py
│   │   │   │   ├── elasticsearch.py
│   │   │   │   └── minio.py
│   │   │   ├── export/
│   │   │   │   ├── csv_handler.py
│   │   │   │   ├── excel_handler.py
│   │   │   │   ├── sql_handler.py
│   │   │   │   └── json_handler.py
│   │   │   ├── query.py
│   │   │   ├── task.py
│   │   │   └── ai.py
│   │   ├── models/
│   │   │   ├── datasource.py
│   │   │   ├── saved_sql.py
│   │   │   └── export_task.py
│   │   ├── schemas/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   └── database.py
│   │   └── main.py
│   ├── alembic/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── QueryEditor.vue
│   │   │   ├── DataSourceManage.vue
│   │   │   ├── SavedSqlList.vue
│   │   │   ├── TaskList.vue
│   │   │   └── Settings.vue
│   │   ├── components/
│   │   │   ├── SqlEditor.vue
│   │   │   ├── ResultTable.vue
│   │   │   ├── ExportModal.vue
│   │   │   └── AiChat.vue
│   │   ├── api/
│   │   └── stores/
│   ├── Dockerfile
│   ├── nginx.conf
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
├── exports/
└── docs/
```

## 数据模型

### 数据源配置 (datasources)

```sql
CREATE TABLE datasources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL,                 -- postgres/clickhouse/redis 等
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    database VARCHAR(100),
    username VARCHAR(100),
    password_encrypted TEXT,                   -- AES 加密存储
    extra_config JSONB,                        -- 额外配置
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**extra_config 字段说明**:

| 数据源 | extra_config 内容 |
|--------|-------------------|
| PostgreSQL | schema, ssl |
| ClickHouse | cluster, ssl |
| Doris | catalog |
| Redis | cluster_nodes, ssl |
| Redis-Cluster | nodes[], ssl |
| Elasticsearch | ssl, api_key, index_pattern |
| MinIO | secure, region, access_style |

### 保存的 SQL (saved_sqls)

```sql
CREATE TABLE saved_sqls (
    id SERIAL PRIMARY KEY,
    datasource_id INTEGER REFERENCES datasources(id),
    name VARCHAR(200) NOT NULL,
    sql_text TEXT NOT NULL,
    comment TEXT,                              -- 用于 AI 语义匹配
    tags VARCHAR(100)[],
    embedding vector(1536),                    -- comment 的向量表示
    run_count INTEGER DEFAULT 0,
    last_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 向量索引
CREATE INDEX ON saved_sqls USING ivfflat (embedding vector_cosine_ops);
```

### 导出任务 (export_tasks)

```sql
CREATE TABLE export_tasks (
    id SERIAL PRIMARY KEY,
    datasource_id INTEGER REFERENCES datasources(id),
    saved_sql_id INTEGER REFERENCES saved_sqls(id),
    sql_text TEXT NOT NULL,
    export_format VARCHAR(20) NOT NULL,        -- csv/excel/sql/json
    status VARCHAR(20) DEFAULT 'pending',      -- pending/running/completed/failed
    file_path TEXT,
    row_count INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

### AI 配置 (ai_configs)

```sql
CREATE TABLE ai_configs (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(50) NOT NULL,             -- openai/claude/ollama
    api_key_encrypted TEXT,
    base_url VARCHAR(255),
    model_name VARCHAR(100),
    extra_params JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

## API 设计

### 数据源管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/datasources` | 获取数据源列表 |
| POST | `/api/v1/datasources` | 创建数据源 |
| PUT | `/api/v1/datasources/{id}` | 更新数据源 |
| DELETE | `/api/v1/datasources/{id}` | 删除数据源 |
| POST | `/api/v1/datasources/{id}/test` | 测试连接 |

### 查询执行

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/query/execute` | 执行 SQL（试运行，默认 10 行） |
| POST | `/api/v1/query/format` | SQL 格式化 |
| POST | `/api/v1/query/validate` | SQL 语法校验 |

### SQL 保存管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/saved-sqls` | 获取 SQL 列表 |
| POST | `/api/v1/saved-sqls` | 保存 SQL |
| PUT | `/api/v1/saved-sqls/{id}` | 更新 SQL |
| DELETE | `/api/v1/saved-sqls/{id}` | 删除 SQL |

### 导出任务

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/exports` | 创建导出任务 |
| GET | `/api/v1/exports` | 获取任务列表 |
| GET | `/api/v1/exports/{id}` | 获取任务状态 |
| GET | `/api/v1/exports/{id}/download` | 下载文件 |
| DELETE | `/api/v1/exports/{id}` | 取消/删除任务 |

### AI 生成 SQL

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/ai/generate` | 根据描述生成 SQL |
| GET | `/api/v1/ai/config` | 获取 AI 配置 |
| PUT | `/api/v1/ai/config` | 更新 AI 配置 |

## 核心业务流程

### 数据源连接器设计

采用工厂模式 + 策略模式，统一接口：

```python
class BaseConnector(ABC):
    @abstractmethod
    async def connect(self) -> None: pass

    @abstractmethod
    async def close(self) -> None: pass

    @abstractmethod
    async def test_connection(self) -> bool: pass

    @abstractmethod
    async def execute(self, sql: str, limit: int = None) -> Dict[str, Any]: pass

    @abstractmethod
    async def stream_execute(self, sql: str, batch_size: int = 1000) -> AsyncIterator[List[Any]]: pass

    @abstractmethod
    def get_export_formats(self) -> List[str]: pass
```

### 导出处理流程

```
导出请求 → 预估结果数量
    ├─ 行数 < 阈值 → 同步流式导出，直接返回文件
    └─ 行数 >= 阈值 → 异步任务，后台 Worker 流式处理
```

### AI 生成 SQL 流程

```
用户描述 → 向量化 → 语义匹配 saved_sqls.comment
    ├─ 找到相似 SQL (相似度 > 0.7) → 以相似 SQL 为示例生成
    └─ 未找到 → 直接根据描述生成
```

## 前端设计

### 页面布局

```
┌────────────────────────────────────────────────────────────────────────┐
│  QueryExport                                    [数据源: ▼]  [设置]    │
├────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  SQL 编辑器 (CodeMirror)                    [格式化] [试运行]     │  │
│  │  [💾 保存 SQL]  [📤 导出 ▼]  [🤖 AI 生成]                        │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │  执行结果                                    耗时: xxx  n行       │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────┐  ┌─────────────────────────────┐   │
│  │  保存的 SQL                    │  │  导出任务                    │   │
│  └────────────────────────────────┘  └─────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

### 主要组件

| 组件 | 说明 |
|------|------|
| SqlEditor.vue | CodeMirror 封装，SQL 高亮、补全、格式化 |
| ResultTable.vue | 结果表格，虚拟滚动优化 |
| ExportModal.vue | 导出格式选择，同步/异步选项 |
| AiChat.vue | AI 对话面板 |
| DataSourceForm.vue | 动态表单，根据数据源类型显示字段 |

## 技术依赖

### 后端 (requirements.txt)

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.0
asyncpg>=0.29.0
alembic>=1.13.0
pgvector>=0.2.0
psycopg2-binary>=2.9.9
clickhouse-connect>=0.6.0
mysql-connector-python>=8.0.0
redis>=5.0.0
elasticsearch>=8.12.0
minio>=7.2.0
openpyxl>=3.1.0
xlsxwriter>=3.1.9
httpx>=0.26.0
pydantic>=2.5.0
cryptography>=42.0.0
aiofiles>=23.2.0
```

### 前端 (package.json)

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "axios": "^1.6.0",
    "@codemirror/lang-sql": "^6.6.0",
    "codemirror": "^6.0.0",
    "sql-formatter": "^15.0.0",
    "element-plus": "^2.5.0",
    "vue-virtual-scroller": "^2.0.0"
  }
}
```

## 部署配置

### Docker Compose

```yaml
version: '3.8'

services:
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: ${DB_USER:-queryexport}
      POSTGRES_PASSWORD: ${DB_PASSWORD:-queryexport123}
      POSTGRES_DB: ${DB_NAME:-queryexport}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      - APP_SECRET_KEY=${APP_SECRET_KEY}
      - EXPORT_DIR=/app/exports
    volumes:
      - ./exports:/app/exports
    depends_on:
      - postgres

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
```

### 启动命令

```bash
# 启动服务
docker-compose up -d --build

# 开发模式
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 查看日志
docker-compose logs -f
```

### 访问地址

- 前端界面: http://localhost
- API 文档: http://localhost:8000/docs

## PostgreSQL 扩展要求

```sql
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE saved_sqls ADD COLUMN embedding vector(1536);
CREATE INDEX ON saved_sqls USING ivfflat (embedding vector_cosine_ops);
```
