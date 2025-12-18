"""
Limits checker for local deployment.
All limits are disabled - always return 'can_create: True' / 'can_start: True'.
"""
from typing import Dict, Any
from core.utils.logger import logger

# 本地部署不限制任何资源
DEFAULT_UNLIMITED = 999999


async def check_agent_run_limit(client, account_id: str) -> Dict[str, Any]:
    """检查代理运行限制 - 本地部署无限制"""
    logger.debug(f"Checking agent run limit for account {account_id} - local deployment, no limits")
    return {
        'can_start': True,
        'running_count': 0,
        'running_thread_ids': [],
        'limit': DEFAULT_UNLIMITED
    }


async def check_agent_count_limit(client, account_id: str) -> Dict[str, Any]:
    """检查代理数量限制 - 本地部署无限制"""
    logger.debug(f"Checking agent count limit for account {account_id} - local deployment, no limits")
    return {
        'can_create': True,
        'current_count': 0,
        'limit': DEFAULT_UNLIMITED,
        'tier_name': 'local'
    }


async def check_project_count_limit(client, account_id: str) -> Dict[str, Any]:
    """检查项目数量限制 - 本地部署无限制"""
    logger.debug(f"Checking project count limit for account {account_id} - local deployment, no limits")
    return {
        'can_create': True,
        'current_count': 0,
        'limit': DEFAULT_UNLIMITED,
        'tier_name': 'local'
    }


async def check_trigger_limit(client, account_id: str, agent_id: str = None, trigger_type: str = None) -> Dict[str, Any]:
    """检查触发器限制 - 本地部署无限制"""
    logger.debug(f"Checking trigger limit for account {account_id} - local deployment, no limits")
    if agent_id is None or trigger_type is None:
        return {
            'scheduled': {'current_count': 0, 'limit': DEFAULT_UNLIMITED},
            'app': {'current_count': 0, 'limit': DEFAULT_UNLIMITED},
            'tier_name': 'local'
        }
    return {
        'can_create': True,
        'current_count': 0,
        'limit': DEFAULT_UNLIMITED,
        'tier_name': 'local'
    }


async def check_custom_mcp_limit(client, account_id: str) -> Dict[str, Any]:
    """检查自定义 MCP 限制 - 本地部署无限制"""
    logger.debug(f"Checking custom MCP limit for account {account_id} - local deployment, no limits")
    return {
        'can_create': True,
        'current_count': 0,
        'limit': DEFAULT_UNLIMITED,
        'tier_name': 'local'
    }


async def check_thread_limit(client, account_id: str) -> Dict[str, Any]:
    """检查线程限制 - 本地部署无限制"""
    logger.debug(f"Checking thread limit for account {account_id} - local deployment, no limits")
    return {
        'can_create': True,
        'current_count': 0,
        'limit': DEFAULT_UNLIMITED,
        'tier_name': 'local'
    }
