"""
本地认证模块
替代 Supabase Auth
"""

from .local_auth import router
from fastapi import Depends
from core.utils.auth_utils import verify_admin_api_key

# 从 core.auth.py 中导入下列函数
try:
    from core.auth import get_current_user as _get_current_user
    get_current_user = _get_current_user
except ImportError:
    # 如果 core.auth 不可用，提供默认实现
    async def get_current_user(request=None, credentials=None) -> dict:
        """获取当前用户"""
        return {"user_id": None}


async def require_admin(verified: bool = Depends(verify_admin_api_key)) -> dict:
    """Admin权限验证依赖"""
    return {"is_admin": verified}


async def require_super_admin(verified: bool = Depends(verify_admin_api_key)) -> dict:
    """超级管理员权限验证依赖"""
    return {"is_super_admin": verified}


__all__ = ["router", "require_admin", "require_super_admin", "get_current_user"]
