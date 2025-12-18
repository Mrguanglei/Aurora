"""
中央数据库连接管理 - Mock Supabase Client

私有化部署中 Supabase 已移除，使用 Mock Client 返回空数据
该文件仅保留用于向后兼容性
"""

from typing import Optional, Any, List
from core.utils.logger import logger
from core.utils.config import config
import threading


class MockQueryResult:
    """模拟 Supabase 查询结果"""
    def __init__(self, data: List[Any] = None, count: int = 0):
        self.data = data or []
        self.count = count


class MockQueryBuilder:
    """模拟 Supabase 查询构建器 - 所有查询返回空数据"""
    
    def __init__(self, table_name: str):
        self._table_name = table_name
        self._count_mode = None
    
    def select(self, *args, count: str = None, **kwargs) -> 'MockQueryBuilder':
        if count:
            self._count_mode = count
        return self
    
    def insert(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def update(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def upsert(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def delete(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def eq(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def neq(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def gt(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def gte(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def lt(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def lte(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def like(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def ilike(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def is_(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def in_(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def contains(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def contained_by(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def order(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def limit(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def offset(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def range(self, *args, **kwargs) -> 'MockQueryBuilder':
        return self
    
    def single(self) -> 'MockQueryBuilder':
        return self
    
    def maybe_single(self) -> 'MockQueryBuilder':
        return self
    
    async def execute(self) -> MockQueryResult:
        """执行查询 - 返回空数据"""
        logger.debug(f"MockSupabase: 模拟查询表 '{self._table_name}' - 返回空数据")
        return MockQueryResult(data=[], count=0)


class MockSupabaseClient:
    """模拟 Supabase 客户端 - 所有操作返回空数据或成功"""
    
    def table(self, table_name: str) -> MockQueryBuilder:
        """返回模拟的查询构建器"""
        return MockQueryBuilder(table_name)
    
    async def rpc(self, function_name: str, params: dict = None) -> MockQueryResult:
        """模拟 RPC 调用 - 返回空数据"""
        logger.debug(f"MockSupabase: 模拟 RPC 调用 '{function_name}' - 返回空数据")
        return MockQueryResult(data=[], count=0)


# 全局 Mock 客户端实例
_mock_client = MockSupabaseClient()


class DBConnection:
    """Thread-safe singleton database connection manager.
    
    私有化部署中使用 Mock Client，返回空数据。
    """
    
    _instance: Optional['DBConnection'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        pass

    async def initialize(self):
        """初始化数据库连接 - 使用 Mock Client"""
        if self._initialized:
            return
        logger.info("ℹ️ 使用 Mock Supabase Client（私有化部署，无 Supabase）")
        self._initialized = True

    @classmethod
    async def disconnect(cls):
        """断开数据库连接"""
        if cls._instance:
            cls._instance._initialized = False
            logger.info("✅ Mock 数据库连接已断开")

    @property
    async def client(self) -> MockSupabaseClient:
        """获取 Mock 客户端实例"""
        if not self._initialized:
            await self.initialize()
        return _mock_client
