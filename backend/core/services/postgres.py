"""
本地 PostgreSQL 数据库连接管理
替代 Supabase，用于私有化部署
"""

import asyncpg
from typing import Optional
from core.utils.logger import logger
from core.utils.config import config
import threading

class PostgresConnection:
    """线程安全的 PostgreSQL 连接池管理器"""
    
    _instance: Optional['PostgresConnection'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._pool = None
        return cls._instance

    def __init__(self):
        pass

    async def initialize(self):
        """初始化数据库连接池"""
        if self._initialized:
            return
        
        try:
            database_url = config.DATABASE_URL
            if not database_url:
                raise RuntimeError("DATABASE_URL 环境变量未设置")
            
            # 创建连接池
            self._pool = await asyncpg.create_pool(
                database_url,
                min_size=5,
                max_size=20,
                command_timeout=60,
                server_settings={"jit": "off"},
            )
            
            self._initialized = True
            logger.info("✅ PostgreSQL 连接池初始化成功")
            
        except Exception as e:
            logger.error(f"❌ 数据库连接错误: {e}")
            raise RuntimeError(f"数据库连接失败: {str(e)}")

    @classmethod
    async def disconnect(cls):
        """关闭数据库连接"""
        if cls._instance and cls._instance._pool:
            try:
                await cls._instance._pool.close()
                cls._instance._initialized = False
                cls._instance._pool = None
                logger.info("✅ PostgreSQL 连接已关闭")
            except Exception as e:
                logger.warning(f"⚠️  关闭连接时出错: {e}")

    @property
    async def pool(self) -> asyncpg.Pool:
        """获取连接池实例"""
        if not self._initialized:
            await self.initialize()
        if not self._pool:
            raise RuntimeError("数据库未初始化")
        return self._pool

    async def get_connection(self):
        """获取单个数据库连接"""
        pool = await self.pool
        return pool.acquire()

    async def execute(self, query: str, *args):
        """执行查询（不返回结果）"""
        pool = await self.pool
        async with pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def fetch(self, query: str, *args):
        """获取多行数据"""
        pool = await self.pool
        async with pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchval(self, query: str, *args):
        """获取单个值"""
        pool = await self.pool
        async with pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def fetchrow(self, query: str, *args):
        """获取单行数据"""
        pool = await self.pool
        async with pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def transaction(self):
        """获取事务上下文"""
        pool = await self.pool
        conn = await pool.acquire()
        return conn

    async def close_connection(self, conn):
        """关闭连接"""
        if conn:
            await conn.close()
