"""
本地认证 API - 用户注册、登录、令牌管理
替代 Supabase Auth
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from typing import Optional
import uuid
from datetime import datetime, timezone
from core.services.postgres import PostgresConnection
from core.services.jwt_service import jwt_service
from core.utils.logger import logger

router = APIRouter(prefix="/auth", tags=["auth"])

# ============================================================================
# 数据模型
# ============================================================================

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str
    email: str
    name: Optional[str] = None
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# ============================================================================
# 认证端点
# ============================================================================

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest):
    """用户注册"""
    try:
        logger.debug(f"Register attempt for email: {req.email}")
        db = PostgresConnection()
        await db.initialize()
        
        # 检查邮箱是否已存在
        existing = await db.fetchrow(
            "SELECT id FROM users WHERE email = $1",
            req.email.lower()
        )
        
        if existing:
            logger.warning(f"Registration failed: email already exists {req.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        # 创建新用户
        user_id = str(uuid.uuid4())
        password_hash = jwt_service.hash_password(req.password)
        now = datetime.now(timezone.utc).isoformat()
        
        await db.execute(
            """
            INSERT INTO users (id, email, username, password_hash, created_at, updated_at, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, TRUE)
            """,
            user_id,
            req.email.lower(),
            req.name or req.email.split("@")[0],
            password_hash,
            now,
            now
        )
        
        logger.info(f"✅ 新用户注册: {req.email} (ID: {user_id})")
        
        # 创建 tokens
        access_token = jwt_service.create_access_token(user_id, req.email)
        refresh_token = jwt_service.create_refresh_token(user_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            email=req.email,
            name=req.name or req.email.split("@")[0]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 注册错误: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败"
        )

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """用户登录"""
    try:
        db = PostgresConnection()
        await db.initialize()
        
        # 查找用户
        user = await db.fetchrow(
            "SELECT id, email, username, password_hash FROM users WHERE email = $1 AND is_active = TRUE",
            req.email.lower()
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )
        
        # 验证密码
        if not jwt_service.verify_password(req.password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误"
            )
        
        # 更新最后登录时间
        now = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "UPDATE users SET last_login_at = $1 WHERE id = $2",
            now,
            user["id"]
        )
        
        logger.info(f"✅ 用户登录: {req.email}")
        
        # 创建 tokens
        access_token = jwt_service.create_access_token(user["id"], user["email"])
        refresh_token = jwt_service.create_refresh_token(user["id"])
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user["id"],
            email=user["email"],
            name=user["username"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 登录错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败"
        )

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(req: RefreshTokenRequest):
    """刷新 access token"""
    try:
        # 验证 refresh token
        payload = jwt_service.verify_token(req.refresh_token)
        
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 refresh token"
            )
        
        user_id = payload.get("user_id")
        db = PostgresConnection()
        await db.initialize()
        
        # 获取用户信息
        user = await db.fetchrow(
            "SELECT email, username FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )
        
        # 创建新的 access token
        access_token = jwt_service.create_access_token(user_id, user["email"])
        refresh_token = jwt_service.create_refresh_token(user_id)
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user_id,
            email=user["email"],
            name=user["username"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Token 刷新错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token 刷新失败"
        )

@router.get("/me")
async def get_current_user(authorization: str = None):
    """获取当前用户信息"""
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少认证令牌"
            )
        
        token = authorization[7:]  # 移除 "Bearer " 前缀
        payload = jwt_service.verify_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效或过旧的令牌"
            )
        
        user_id = payload.get("user_id")
        db = PostgresConnection()
        await db.initialize()
        
        # 获取用户信息
        user = await db.fetchrow(
            "SELECT id, email, username, created_at FROM users WHERE id = $1",
            user_id
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        return {
            "id": user["id"],
            "email": user["email"],
            "name": user["username"],
            "created_at": user["created_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取用户信息错误: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )
