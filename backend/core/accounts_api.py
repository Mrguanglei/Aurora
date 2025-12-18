"""
Accounts API
Handles user account operations
"""

from fastapi import APIRouter, HTTPException, Depends
from core.utils.auth_utils import verify_and_get_user_id_from_jwt
from core.services.postgres import PostgresConnection
from core.utils.logger import logger

router = APIRouter(tags=["accounts"])

@router.get("/accounts", summary="Get User Accounts", operation_id="get_user_accounts")
async def get_user_accounts(
    user_id: str = Depends(verify_and_get_user_id_from_jwt)
):
    """
    私有化部署版本：从本地 PostgreSQL 的 users 表返回当前用户的“账号”信息。
    这里简化为：每个用户只有一个隐含的 account，即自己的用户记录。
    """
    try:
        db = PostgresConnection()
        pool = await db.pool
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, email, username, created_at, updated_at, is_active
                FROM users
                WHERE id = $1
                """,
                user_id,
            )

        if not row:
            return []
        
        # 保持前端预期：返回 account 列表
        return [
            {
                "id": str(row["id"]),
                "email": row["email"],
                "username": row["username"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "is_active": row["is_active"],
            }
        ]
        
    except Exception as e:
        logger.error(f"Error fetching user accounts from PostgreSQL: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch accounts")

