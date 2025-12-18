"""
JWT 认证服务 - 本地管理认证令牌
替代 Supabase Auth
"""

import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from core.utils.logger import logger
from core.utils.config import config
import hashlib

class JWTService:
    """JWT token 管理和验证"""
    
    def __init__(self):
        self.secret_key = config.JWT_SECRET_KEY or self._generate_secret()
        self.algorithm = "HS256"
        self.access_token_expire_minutes = 24 * 60  # 24 小时
        self.refresh_token_expire_days = 30  # 30 天

    @staticmethod
    def _generate_secret() -> str:
        """生成新的密钥"""
        return secrets.token_urlsafe(32)

    def create_access_token(self, user_id: str, email: str, data: Optional[Dict[str, Any]] = None) -> str:
        """创建访问 token"""
        try:
            if data is None:
                data = {}
            
            to_encode = {
                "user_id": user_id,
                "email": email,
                "type": "access",
                **data
            }
            
            expire = datetime.now(timezone.utc) + timedelta(minutes=self.access_token_expire_minutes)
            to_encode.update({"exp": expire})
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"✅ 创建 access token: user_id={user_id}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"❌ 创建 token 失败: {e}")
            raise

    def create_refresh_token(self, user_id: str) -> str:
        """创建刷新 token"""
        try:
            to_encode = {
                "user_id": user_id,
                "type": "refresh",
            }
            
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
            to_encode.update({"exp": expire})
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            logger.debug(f"✅ 创建 refresh token: user_id={user_id}")
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"❌ 创建 refresh token 失败: {e}")
            raise

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证并解析 token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            user_id: str = payload.get("user_id")
            
            if user_id is None:
                logger.warning("⚠️  Token 中缺少 user_id")
                return None
            
            logger.debug(f"✅ Token 验证成功: user_id={user_id}")
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("⚠️  Token 已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"⚠️  Invalid token: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Token 验证错误: {e}")
            return None

    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码"""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """验证密码"""
        return hashlib.sha256(password.encode()).hexdigest() == hashed


# 全局 JWT 服务实例
jwt_service = JWTService()
