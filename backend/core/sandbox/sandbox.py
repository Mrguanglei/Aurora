"""
Sandbox module - replaced Daytona with Docker-based on-demand container management.

This module provides functions to create, manage, and delete Docker sandbox containers
for agent execution. Each sandbox is created on-demand and deleted after use.
"""

from core.sandbox.docker_sandbox import (
    create_sandbox as _create_sandbox,
    get_or_start_sandbox as _get_or_start_sandbox,
    delete_sandbox as _delete_sandbox,
    DockerSandbox,
    get_docker_client
)
from core.utils.logger import logger
import asyncio


# Re-export functions with same interface
async def create_sandbox(password: str, project_id: str = None):
    """
    Create a new Docker sandbox container on-demand.
    
    Args:
        password: VNC password for the sandbox
        project_id: Optional project ID to label the container
        
    Returns:
        DockerSandbox wrapper object
    """
    sandbox, container_id = await _create_sandbox(password, project_id)
    logger.info(f"Sandbox created with ID: {sandbox.id}")
    logger.info(f"Sandbox environment successfully initialized")
    return sandbox


async def get_or_start_sandbox(sandbox_id: str):
    """
    Retrieve a sandbox by ID, check its state, and start it if needed.
    
    Args:
        sandbox_id: The container ID or name
        
    Returns:
        DockerSandbox wrapper object
    """
    sandbox = await _get_or_start_sandbox(sandbox_id)
    logger.info(f"Sandbox {sandbox_id} is ready")
    return sandbox


async def delete_sandbox(sandbox_id: str) -> bool:
    """
    Delete a sandbox by its ID.
    
    Args:
        sandbox_id: The container ID or name
        
    Returns:
        True if successful
    """
    result = await _delete_sandbox(sandbox_id)
    if result:
        logger.info(f"Successfully deleted sandbox {sandbox_id}")
    return result
