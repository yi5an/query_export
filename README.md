# QueryExport

QueryExport 是一个面向数据查询与导出的轻量工作台，提供多数据源管理、只读查询、保存 SQL、AI 辅助生成 SQL 和异步导出任务能力。

## 功能概览

- 支持 PostgreSQL、ClickHouse、Doris、Redis、Elasticsearch、MinIO 等数据源接入
- SQL 类型数据源默认启用只读限制，拒绝写操作和多语句执行
- 支持保存 SQL、相似 SQL 检索与 AI 生成 SQL
- 支持 CSV、Excel、SQL 导出，异步任务默认保留 7 天
- 提供 Vue 3 前端和 FastAPI 后端，适合 Docker 化部署

## 技术栈

- 前端：Vue 3、TypeScript、Vite、Element Plus、CodeMirror
- 后端：FastAPI、SQLAlchemy、Alembic、PostgreSQL
- 部署：Docker Compose

## 目录结构

```text
backend/      FastAPI 后端、连接器、导出服务、Alembic 迁移
frontend/     Vue 前端、页面、组件、API 客户端
docs/         设计、计划与部署文档
docker-compose.yml
```

## 快速开始

1. 准备环境变量：

```bash
cp .env.example .env
```

2. 启动服务：

```bash
docker compose up -d --build
```

3. 访问服务：

- 前端：`http://127.0.0.1:21180`
- 后端：`http://127.0.0.1:8081`
- API 文档：`http://127.0.0.1:8081/docs`

## 开发命令

前端本地开发：

```bash
cd frontend
npm install
npm run dev
```

前端构建校验：

```bash
cd frontend
npm run build
```

后端语法检查：

```bash
python3 -m compileall backend/app
```

## 部署与说明

- 部署说明见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- 贡献规范见 [AGENTS.md](AGENTS.md)
