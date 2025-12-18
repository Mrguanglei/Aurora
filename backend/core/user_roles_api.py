"""
User Roles API
Handles user role operations
"""

from fastapi import APIRouter, Depends
from core.utils.auth_utils import verify_and_get_user_id_from_jwt
from core.utils.logger import logger
from core.services.postgres import PostgresConnection

router = APIRouter(tags=["user-roles"])

@router.get("/user-roles", summary="Get User Admin Role", operation_id="get_user_admin_role")
async def get_user_admin_role(
    user_id: str = Depends(verify_and_get_user_id_from_jwt)
):
    """Get admin role for the current user (local PostgreSQL implementation).

    逻辑：
    1. 从本地 PostgreSQL 的 users 表读取 email 和 is_admin 字段
    2. 如果 is_admin = TRUE，则视为管理员
    3. 为了兼容，你的邮箱 mrguanglei@163.com 也会被视为管理员（即使 is_admin 还没手动置为 TRUE）
    """

    target_admin_email = "mrguanglei@163.com"

    try:
        db = PostgresConnection()
        pool = await db.pool
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT email, is_admin
                FROM users
                WHERE id = $1
                """,
                user_id,
            )

        email = row["email"] if row else None
        is_admin_flag = bool(row["is_admin"]) if row and "is_admin" in row else False

        # 1) 数据库里 is_admin = TRUE 的，一律视为管理员
        if is_admin_flag:
            logger.debug(
                f"User roles endpoint: user_id={user_id}, email={email}, is_admin={is_admin_flag} -> admin"
            )
            return {
                "isAdmin": True,
                "role": "admin",
            }

        # 2) 兼容：你的邮箱也视为管理员（方便你直接用）
        if email == target_admin_email:
            logger.debug(
                f"User roles endpoint: user_id={user_id}, email={email} (hardcoded admin) -> admin"
            )
            return {
                "isAdmin": True,
                "role": "admin",
            }

        logger.debug(
            f"User roles endpoint: user_id={user_id}, email={email}, is_admin={is_admin_flag} -> non-admin"
        )
        return {
            "isAdmin": False,
            "role": None,
        }

    except Exception as e:
        logger.error(f"Error determining admin role from PostgreSQL: {str(e)}")
        return {
            "isAdmin": False,
            "role": None,
        }

