from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.api.v1 import ai, datasources, queries, exports, saved_sql

settings = get_settings()

app = FastAPI(
    title="QueryExport API",
    description="SQL 查询与导出工具",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# 注册路由
app.include_router(datasources.router, prefix="/api/v1/datasources", tags=["数据源"])
app.include_router(queries.router, prefix="/api/v1/query", tags=["查询"])
app.include_router(exports.router, prefix="/api/v1/exports", tags=["导出"])
app.include_router(saved_sql.router, prefix="/api/v1/saved-sqls", tags=["保存的SQL"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])


@app.get("/")
async def root():
    return {"message": "QueryExport API", "version": "1.0.0"}


@app.get("/health")
async def health():
    return {"status": "healthy"}
