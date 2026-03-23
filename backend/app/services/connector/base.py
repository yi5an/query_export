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
