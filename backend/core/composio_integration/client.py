import os
from typing import Optional
from composio_client import Composio
from core.utils.logger import logger


class ComposioClient:
    _instance: Optional[Composio] = None
    
    @classmethod
    def get_client(cls, api_key: Optional[str] = None) -> Optional[Composio]:
        if cls._instance is None:
            if not api_key:
                api_key = os.getenv("COMPOSIO_API_KEY")
                if not api_key:
                    logger.warning("COMPOSIO_API_KEY not configured, Composio features will be unavailable")
                    return None
            
            logger.debug("Initializing Composio client")
            cls._instance = Composio(api_key=api_key)
        
        return cls._instance
    
    @classmethod
    def reset_client(cls) -> None:
        cls._instance = None


def get_composio_client(api_key: Optional[str] = None) -> Optional[Composio]:
    return ComposioClient.get_client(api_key) 