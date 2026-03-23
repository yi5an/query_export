from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖"""
    async with get_db() as session:
        yield session
