from fastapi import HTTPException, Depends, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from core.services.supabase import DBConnection
from core.utils.logger import logger

security = HTTPBearer(auto_error=False)  # Don't auto-error, we handle both API key and Bearer

async def get_current_user(request: Request, credentials: Optional[HTTPAuthorizationCredentials] = Security(security)) -> dict:
    """
    Authenticate user via either X-API-Key header or Bearer token.
    Supports both authentication methods for all endpoints.
    """
    from core.utils.auth_utils import verify_and_get_user_id_from_jwt
    try:
        user_id = await verify_and_get_user_id_from_jwt(request)
        # Get token from credentials if available (for backwards compatibility)
        token = credentials.credentials if credentials else None
        logger.debug(f"Successfully authenticated user: {user_id[:8]}...")
        return {"user_id": user_id, "token": token}
    except HTTPException as e:
        # Re-raise HTTPExceptions with their original detail
        logger.warning(f"Authentication failed for {request.url.path}: {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Auth failed: {e}", exc_info=True)
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

def verify_role(required_role: str):
    async def role_checker(user: dict = Depends(get_current_user)) -> dict:
        db = DBConnection()
        client = await db.client
        user_id = user['user_id']
        
        logger.debug(f"Checking role for user {user_id[:8]}..., required: {required_role}")
        
        # First check user_roles table
        result = await client.table('user_roles').select('role').eq('user_id', user_id).execute()
        
        user_role = None
        if result.data and len(result.data) > 0:
            user_role = result.data[0]['role']
            logger.debug(f"User {user_id[:8]}... has role from user_roles table: {user_role}")
        else:
            # If no role in user_roles table, check users.is_admin field
            logger.debug(f"User {user_id[:8]}... not found in user_roles table, checking users.is_admin")
            try:
                from core.services.postgres import PostgresConnection
                postgres_db = PostgresConnection()
                pool = await postgres_db.pool
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        """
                        SELECT email, is_admin
                        FROM users
                        WHERE id = $1
                        """,
                        user_id,
                    )
                
                if row:
                    email = row.get("email")
                    is_admin_flag = bool(row.get("is_admin", False))
                    
                    # Check hardcoded admin email for compatibility
                    target_admin_email = "mrguanglei@163.com"
                    if is_admin_flag or (email == target_admin_email):
                        user_role = 'admin'
                        logger.debug(f"User {user_id[:8]}... is admin (is_admin={is_admin_flag}, email={email})")
                    else:
                        user_role = 'user'
                        logger.debug(f"User {user_id[:8]}... is not admin (is_admin={is_admin_flag}, email={email})")
                else:
                    logger.warning(f"User {user_id[:8]}... not found in users table")
                    user_role = 'user'
            except Exception as e:
                logger.error(f"Error checking users.is_admin for user {user_id[:8]}...: {e}", exc_info=True)
                user_role = 'user'
        
        if not user_role:
            logger.warning(f"User {user_id[:8]}... has no role assigned")
            raise HTTPException(status_code=403, detail="No role assigned")
        
        role_hierarchy = {'user': 0, 'admin': 1, 'super_admin': 2}
        
        if role_hierarchy.get(user_role, -1) < role_hierarchy.get(required_role, 999):
            logger.warning(f"User {user_id[:8]}... with role {user_role} does not have required role {required_role}")
            raise HTTPException(status_code=403, detail=f"Requires {required_role} role")
        
        user['role'] = user_role
        logger.debug(f"Role check passed for user {user_id[:8]}... with role {user_role}")
        return user
    
    return role_checker

require_admin = verify_role('admin')
require_super_admin = verify_role('super_admin') 