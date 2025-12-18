import hmac
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks, Request
from pydantic import BaseModel
from typing import Dict, Optional
from datetime import datetime, timezone
import os
import concurrent.futures
from core.utils.auth_utils import verify_and_get_user_id_from_jwt
from core.utils.logger import logger
from core.utils.config import config
# 已删除账单系统
# from core.billing.subscriptions import free_tier_service
from core.utils.suna_default_agent_service import SunaDefaultAgentService
from core.services.supabase import DBConnection
from core.services.email import email_service

# Main setup router (prefix="/setup")
router = APIRouter(prefix="/setup", tags=["setup"])

webhook_router = APIRouter(tags=["webhooks"])  # 已删除Webhook系统

# ============================================================================
# Models
# ============================================================================

# 已删除Webhook相关代码

# ============================================================================
# Helper Functions
# ============================================================================

async def initialize_user_account(account_id: str, email: Optional[str] = None, user_record: Optional[dict] = None) -> Dict:
    try:
        logger.info(f"[SETUP] Initializing account for {account_id}")
        
        db = DBConnection()
        await db.initialize()

        user_name = None
        if user_record and email:
            user_name = _extract_user_name(user_record, email)
        

        from core.notifications.notification_service import notification_service

        logger.info(f"[SETUP] Sending welcome email to {email} with name {user_name}")
        try:
            await notification_service.send_welcome_email(account_id)
            
        except Exception as ex:
            logger.error(f"[SETUP] Error sending welcome notification: {ex}")
            if email and user_name:
                _send_welcome_email_async(email, user_name)
        
# 已删除billing
        # result = await free_tier_service.auto_subscribe_to_free_tier(account_id, email)
        # For private deployment, skip billing setup
        result = {'success': True, 'subscription_id': None}
        
        logger.info(f"[SETUP] Installing Suna agent for {account_id}")
        suna_service = SunaDefaultAgentService(db)
        agent_id = await suna_service.install_suna_agent_for_user(account_id)
        

        if not agent_id:
            logger.warning(f"[SETUP] Failed to install Suna agent for {account_id}, but continuing")
        
        if user_record:
            # 已删除推荐代码处理
            pass
        
        logger.info(f"[SETUP] ✅ Account initialization complete for {account_id}")
        
        return {
            'success': True,
            'message': 'Account initialized successfully',
            'subscription_id': result.get('subscription_id'),
            'agent_id': agent_id
        }
        
    except Exception as e:
        logger.error(f"[SETUP] Error initializing account {account_id}: {e}")
        return {
            'success': False,
            'message': str(e),
            'error': str(e)
        }

def _extract_user_name(user_record: dict, email: str) -> str:
    """Extract user name from metadata or email"""
    raw_user_metadata = user_record.get('raw_user_meta_data', {})
    return (
        raw_user_metadata.get('full_name') or 
        raw_user_metadata.get('name') or
        email.split('@')[0].replace('.', ' ').replace('_', ' ').replace('-', ' ').title()
    )

def _send_welcome_email_async(email: str, user_name: str):
    """Send welcome email asynchronously (non-blocking)"""
    try:
        return email_service.send_welcome_email(
            user_email=email,
            user_name=user_name
        )
    except Exception as e:
        logger.error(f"Failed to send welcome email to {email}: {e}")
        return None

# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/initialize")
async def initialize_account(
    account_id: str = Depends(verify_and_get_user_id_from_jwt)
):
    db = DBConnection()
    await db.initialize()
    client = await db.client
    
    email = None
    user_record = None
    
    try:
        user_response = await client.auth.admin.get_user_by_id(account_id)
        if user_response and hasattr(user_response, 'user') and user_response.user:
            user = user_response.user
            email = user.email
            user_record = {
                'id': user.id,
                'email': user.email,
                'raw_user_meta_data': user.user_metadata or {}
            }
    except Exception as e:
        logger.warning(f"[SETUP] Could not fetch user for initialization: {e}")
    
    result = await initialize_user_account(account_id, email, user_record)
    
    if not result.get('success'):
        raise HTTPException(status_code=500, detail=result.get('message', 'Failed to initialize account'))
    
    return result

# ============================================================================
# Webhook Endpoints - 已删除
# ============================================================================
# Webhook endpoints removed for private deployment
# Users will call /setup/initialize endpoint directly
