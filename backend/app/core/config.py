from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    """应用配置"""
    app_name: str = "QueryExport"
    app_secret_key: str = "change-me-in-production"
    database_url: str = "postgresql+asyncpg://user:pass@localhost/queryexport"
    export_dir: str = "/app/exports"
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"

    # CORS 配置
    cors_origins: list[str] = ["*"]  # 开发环境允许所有，生产环境应限制
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["*"]
    cors_allow_headers: list[str] = ["*"]

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()