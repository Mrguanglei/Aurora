"""
中央数据库连接管理 - Supabase (已删除，仅用于沐兼容性)

私有化部署中已改用本地 PostgreSQL
该文件仅保留用于向后兼容性
"""

from typing import Optional
from core.utils.logger import logger
from core.utils.config import config
import threading

# 尝试导入 Supabase，但如果不可用则安全忽略
try:
    from supabase import create_async_client, AsyncClient
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.debug("⚠️ Supabase SDK 不可用")

class DBConnection:
    """Thread-safe singleton database connection manager using Supabase."""
    
    _instance: Optional['DBConnection'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._client = None
        return cls._instance

    def __init__(self):
        """No initialization needed in __init__ as it's handled in __new__"""
        pass

    async def initialize(self):
        """初始化数据库连接。
        
        注意：Supabase 已在私有化部署中移除。
        改用本地 PostgreSQL。
        此方法保留用于兼容性，实际上是无操作的。
        """
        if self._initialized:
            return
        
        # 如果 Supabase 不可用，直接返回
        if not SUPABASE_AVAILABLE:
            logger.info("ℹ️ Supabase 已禁用（私有化部署）。使用本地 PostgreSQL 代替。")
            self._initialized = True
            return
        
        try:
            supabase_url = config.SUPABASE_URL
            supabase_key = config.SUPABASE_SERVICE_ROLE_KEY or config.SUPABASE_ANON_KEY
            
            # 如果未配置 Supabase，安全跳过
            if not supabase_url or not supabase_key:
                logger.info("ℹ️ Supabase 未配置（私有化部署）。跳过 Supabase 初始化。")
                self._initialized = True
                return
            
            # 创建 Supabase 客户端
            self._client = await create_async_client(
                supabase_url, 
                supabase_key,
            )
            
            self._initialized = True
            key_type = "SERVICE_ROLE_KEY" if config.SUPABASE_SERVICE_ROLE_KEY else "ANON_KEY"
            logger.info(f"✅ Supabase 连接初始化（使用 {key_type}）")
            
        except Exception as e:
            logger.warning(f"⚠️ Supabase 初始化失败: {e}。继续使用本地 PostgreSQL。")
            self._initialized = True  # 标记为已初始化，避免重复尝试

    @classmethod
    async def disconnect(cls):
        """断开数据库连接。"""
        if cls._instance and cls._instance._client:
            try:
                # 关闭Supabase 客户端
                if hasattr(cls._instance._client, 'close'):
                    await cls._instance._client.close()
                    
            except Exception as e:
                logger.warning(f"⚠️ 断开连接时错误: {e}")
            finally:
                cls._instance._initialized = False
                cls._instance._client = None
                logger.info("✅ 数据库已断开")

    @property
    async def client(self):
        """获取 Supabase 客户端实例。
        
        注意：在私有化部署中此方法更多是为了向后兼容性。
        实际上改用本地 PostgreSQL 客户端。
        """
        if not self._initialized:
            await self.initialize()
        if not self._client:
            logger.debug("⚠️ Supabase 客户端未可用（使用本地 PostgreSQL）")
            return None
        return self._client
