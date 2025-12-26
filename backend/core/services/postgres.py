"""
本地 PostgreSQL 数据库连接管理
替代 Supabase，用于私有化部署
"""

import asyncpg
from typing import Optional
from core.utils.logger import logger
from core.utils.config import config
import threading
import os

class PostgresConnection:
    """线程安全的 PostgreSQL 连接池管理器"""
    
    _instance: Optional['PostgresConnection'] = None
    _lock = threading.Lock()
    _migration_lock = threading.Lock()
    _migration_done = False

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
            
            # 运行数据库迁移（仅执行一次，根据环境变量控制）
            run_migrations = os.getenv('RUN_MIGRATIONS', 'true').lower() == 'true'
            if run_migrations and not PostgresConnection._migration_done:
                with PostgresConnection._migration_lock:
                    if not PostgresConnection._migration_done:
                        await self._run_migrations()
                        PostgresConnection._migration_done = True
            
        except Exception as e:
            logger.error(f"❌ 数据库连接错误: {e}")
            raise RuntimeError(f"数据库连接失败: {str(e)}")
    
    async def _run_migrations(self):
        """运行数据库迁移脚本"""
        try:
            migration_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "migrations",
                "01_init_schema.sql"
            )

            if not os.path.exists(migration_file):
                logger.warning(f"⚠️  迁移文件不存在: {migration_file}")
                return

            logger.debug(f"Loading migration file from: {migration_file}")
            with open(migration_file, 'r', encoding='utf-8') as f:
                migration_sql = f.read()

            # 智能分割 SQL 语句，正确处理 $$ 美元引号
            statements = self._split_sql_statements(migration_sql)
            logger.debug(f"Found {len(statements)} SQL statements")

            pool = await self.pool
            async with pool.acquire() as conn:
                # 使用数据库级别的advisory lock防止并发迁移
                # 锁ID: 123456789 (任意唯一数字)
                await conn.execute("SELECT pg_advisory_lock(123456789)")

                try:
                    for i, statement in enumerate(statements):
                        try:
                            await conn.execute(statement)
                            logger.debug(f"Executed migration statement {i+1}/{len(statements)}")
                        except Exception as e:
                            error_msg = str(e).lower()
                            # 忽略 "already exists" 类的错误（包括触发器、表、索引等）
                            # 因为我们使用了 IF NOT EXISTS 或 DROP IF EXISTS
                            if ("already exists" not in error_msg and
                                "duplicate" not in error_msg and
                                "trigger" not in error_msg and
                                "does not exist" not in error_msg):  # 也忽略不存在的对象
                                logger.warning(f"⚠️  执行 SQL 语句时出错 ({i+1}): {statement[:80]}... Error: {e}")
                            else:
                                # 静默忽略已存在的对象错误
                                logger.debug(f"跳过已存在的对象: {statement[:60]}...")
                finally:
                    # 确保释放锁
                    await conn.execute("SELECT pg_advisory_unlock(123456789)")

            logger.info("✅ 数据库迁移执行成功")
        except Exception as e:
            logger.error(f"❌ 数据库迁移错误: {e}", exc_info=True)
            # 继续执行，因为表可能已经存在
    
    @staticmethod
    def _split_sql_statements(sql_content: str) -> list:
        """简单分割 SQL 语句，按分号分割并处理美元引号"""
        # 预处理：将美元引号内容替换为占位符
        import re

        # 匹配 $$ ... $$ 或 $tag$ ... $tag$ 的内容
        dollar_pattern = r'\$\$[\s\S]*?\$\$|\$[a-zA-Z_][a-zA-Z0-9_]*\$[\s\S]*?\$[a-zA-Z_][a-zA-Z0-9_]*\$'

        placeholders = []
        def replace_dollar(match):
            placeholders.append(match.group(0))
            return f"__DOLLAR_PLACEHOLDER_{len(placeholders)-1}__"

        # 替换美元引号内容
        processed_content = re.sub(dollar_pattern, replace_dollar, sql_content)

        # 按分号分割
        raw_statements = processed_content.split(';')

        statements = []
        for stmt in raw_statements:
            stmt = stmt.strip()
            if not stmt or stmt.startswith('--'):
                continue

            # 恢复美元引号内容
            for i, placeholder in enumerate(placeholders):
                stmt = stmt.replace(f"__DOLLAR_PLACEHOLDER_{i}__", placeholder)

            statements.append(stmt + ';')

        return statements

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
