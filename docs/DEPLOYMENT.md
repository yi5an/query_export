# QueryExport 部署文档

## 1. 部署结构

当前仓库的代码目录如下：

- `backend/`: FastAPI 后端
- `frontend/`: Vue 3 前端
- `docker-compose.yml`: Docker Compose 编排文件

说明：

- 后端与前端源码都在仓库根目录。
- 当前推荐的容器化部署入口是根目录 `docker-compose.yml`。

## 2. 环境要求

建议环境：

- Docker 24+
- Docker Compose v2
- 可用的 8081、21180 端口

如果服务器已经占用了这些端口，可在根目录 `.env` 中调整。

## 3. 环境变量

在仓库根目录准备 `.env` 文件。当前可用变量示例：

```env
DB_USER=queryexport
DB_PASSWORD=queryexport123
DB_NAME=queryexport
APP_SECRET_KEY=change-me-in-production
BACKEND_PORT=8081
FRONTEND_PORT=21180
```

生产环境至少要修改：

- `DB_PASSWORD`
- `APP_SECRET_KEY`
- `BACKEND_PORT` / `FRONTEND_PORT`（如有端口冲突）

## 4. 启动方式

首次构建并启动：

```bash
docker compose up -d --build
```

说明：

- 后端容器启动时会自动执行 `alembic upgrade head`
- 首次部署会自动初始化 `datasources`、`saved_sqls`、`export_tasks`、`ai_configs` 等表

只重建后端：

```bash
docker compose up -d --build backend
```

只重建前端：

```bash
docker compose up -d --build frontend
```

停止服务：

```bash
docker compose down
```

## 5. 服务访问

默认端口：

- 前端：`http://127.0.0.1:21180`
- 后端：`http://127.0.0.1:8081`
- 后端文档：`http://127.0.0.1:8081/docs`

前端容器内的 `/api/` 会反向代理到后端 `backend:8000`。

## 6. 数据与文件

- PostgreSQL 数据卷：`postgres_data`
- 导出文件目录：`exports/`

如果需要备份导出结果，请备份 `exports/` 目录；如果需要备份数据库，请备份 Docker volume。

## 7. 健康检查与排障

查看容器状态：

```bash
docker ps
```

查看后端日志：

```bash
docker logs --tail 200 queryexport-backend
```

查看前端日志：

```bash
docker logs --tail 200 queryexport-frontend
```

常见问题：

- 后端未启动：先检查 `DB_PASSWORD`、`APP_SECRET_KEY` 是否缺失。
- 前端页面空白：检查 `queryexport-frontend` 日志和 `frontend/nginx.conf` 代理配置。
- 数据源连接失败：确认目标服务地址、端口、认证信息、SSL 配置正确。
- AI 生成失败：确认 AI 配置中的 `base_url`、`model_name`、embedding 配置可用。

## 8. 更新发布

拉取新代码后，建议执行：

```bash
docker compose up -d --build backend frontend
```

如果只改了前端或后端，可单独重建对应服务。
