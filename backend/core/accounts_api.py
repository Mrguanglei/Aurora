"""
Accounts API
Handles user account operations
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field
from typing import Optional
import base64
import uuid
from core.utils.auth_utils import verify_and_get_user_id_from_jwt
from core.services.postgres import PostgresConnection
from core.utils.logger import logger

router = APIRouter(tags=["accounts"])

class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=1, max_length=255)
    avatar_url: Optional[str] = None  # 支持直接设置 avatar_url

@router.post("/account/avatar", summary="Upload User Avatar", operation_id="upload_user_avatar")
async def upload_user_avatar(
    file: UploadFile = File(...),
    user_id: str = Depends(verify_and_get_user_id_from_jwt)
):
    """
    上传用户头像（私有化部署版本）
    将头像转换为 base64 数据 URL 并存储到数据库
    """
    try:
        # 验证文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # 验证文件大小（最大 5MB）
        file_content = await file.read()
        if len(file_content) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size must be less than 5MB")
        
        # 将文件转换为 base64 数据 URL
        base64_data = base64.b64encode(file_content).decode('utf-8')
        data_url = f"data:{file.content_type};base64,{base64_data}"
        
        # 更新用户头像 URL
        db = PostgresConnection()
        pool = await db.pool
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE users
                SET avatar_url = $1
                WHERE id = $2
                RETURNING id, email, username, avatar_url, created_at, updated_at, is_active
                """,
                data_url,
                user_id
            )
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(row["id"]),
            "email": row["email"],
            "username": row["username"],
            "avatar_url": row.get("avatar_url"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_active": row["is_active"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading avatar: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to upload avatar")

@router.patch("/account/profile", summary="Update User Profile", operation_id="update_user_profile")
async def update_user_profile(
    request: UpdateProfileRequest,
    user_id: str = Depends(verify_and_get_user_id_from_jwt)
):
    """
    更新用户资料（私有化部署版本）
    支持更新 username 等字段
    """
    try:
        db = PostgresConnection()
        pool = await db.pool
        
        # 构建更新字段
        update_fields = []
        update_values = []
        param_idx = 1
        
        if request.username is not None:
            update_fields.append(f"username = ${param_idx}")
            update_values.append(request.username)
            param_idx += 1
        
        if request.avatar_url is not None:
            update_fields.append(f"avatar_url = ${param_idx}")
            update_values.append(request.avatar_url)
            param_idx += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # 注意：updated_at 由数据库触发器自动更新，不需要手动设置
        
        # 添加 user_id 作为 WHERE 条件
        update_values.append(user_id)
        
        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = ${param_idx}
            RETURNING id, email, username, avatar_url, created_at, updated_at, is_active
        """
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow(query, *update_values)
        
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "id": str(row["id"]),
            "email": row["email"],
            "username": row["username"],
            "avatar_url": row.get("avatar_url"),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "is_active": row["is_active"],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update profile")

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
                SELECT id, email, username, avatar_url, created_at, updated_at, is_active
                FROM users
                WHERE id = $1
                """,
                user_id,
            )

        if not row:
            return []
        
        # 保持前端预期：返回 account 列表
        # 在本地部署中，每个用户只有一个个人账户
        return [
            {
                "id": str(row["id"]),
                "email": row["email"],
                "username": row["username"],
                "avatar_url": row.get("avatar_url"),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "is_active": row["is_active"],
                "personal_account": True,  # 本地部署中，每个用户都是个人账户
            }
        ]
        
    except Exception as e:
        logger.error(f"Error fetching user accounts from PostgreSQL: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch accounts")

