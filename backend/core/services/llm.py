"""
LLM API interface for making calls to various language models.

This module provides a unified interface for making API calls to different LLM providers
using LiteLLM with simplified error handling and clean parameter management.
"""

from typing import Union, Dict, Any, Optional, AsyncGenerator, List
import os
import json
import asyncio
import litellm
from litellm.router import Router
from litellm.files.main import ModelResponse
from core.utils.logger import logger
from core.utils.config import config
from core.agentpress.error_processor import ErrorProcessor
from pathlib import Path
from datetime import datetime, timezone

# Configure LiteLLM
# os.environ['LITELLM_LOG'] = 'DEBUG'
# litellm.set_verbose = True  # Enable verbose logging
litellm.modify_params = True
litellm.drop_params = True

# Configure LiteLLM retries for transient errors (rate limits, server errors)
# Note: 400 Bad Request errors are handled separately and should not retry
litellm.num_retries = 3

# Enable additional debug logging
# import logging
# litellm_logger = logging.getLogger("LiteLLM")
# litellm_logger.setLevel(logging.DEBUG)
provider_router = None


class LLMError(Exception):
    """Exception for LLM-related errors."""
    pass

def setup_api_keys() -> None:
    """Set up only OpenAI-compatible API keys from environment variables."""
    if not config:
        logger.warning("Config not loaded - skipping API key setup")
        return
        
    # Only care about OpenAI / OpenAI-compatible configuration per current project policy.
    try:
        openai_key = getattr(config, "OPENAI_COMPATIBLE_API_KEY", None) or getattr(config, "OPENAI_API_KEY", None)
        openai_base = getattr(config, "OPENAI_COMPATIBLE_API_BASE", None) or getattr(config, "OPENAI_API_BASE", None)
        if openai_key:
            # expose to environment for downstream libraries if needed
            os.environ["OPENAI_API_KEY"] = openai_key
        if openai_base:
            os.environ["OPENAI_API_BASE"] = openai_base
    except Exception as e:
        logger.debug(f"setup_api_keys skipped non-essential keys: {e}")

def setup_provider_router(openai_compatible_api_key: str = None, openai_compatible_api_base: str = None):
    global provider_router
    
    # Get config values safely
    config_openai_key = getattr(config, 'OPENAI_COMPATIBLE_API_KEY', None) if config else None
    config_openai_base = getattr(config, 'OPENAI_COMPATIBLE_API_BASE', None) if config else None
    # Only include an OpenAI-compatible mapping. The user will provide API base/key/model in env.
    model_list = [
        {
            "model_name": "openai-compatible/*",
            "litellm_params": {
                "model": "openai/*",
                "api_key": openai_compatible_api_key or config_openai_key,
                "api_base": openai_compatible_api_base or config_openai_base,
            },
        },
        # Doubao (ByteDance 豆包) - OpenAI-compatible wrapper
        {
            "model_name": "doubao/*",
            "litellm_params": {
                "model": "openai/*",
                "api_key": getattr(config, 'DOUBAO_API_KEY', None) if config else None,
                "api_base": getattr(config, 'DOUBAO_API_BASE', None) if config else None,
            },
        },
        # DeepSeek via OpenRouter / OpenAI-compatible endpoint
        {
            "model_name": "openrouter/deepseek/*",
            "litellm_params": {
                "model": "openai/*",
                "api_key": getattr(config, 'DEEPSEEK_API_KEY', None) if config else None,
                "api_base": getattr(config, 'DEEPSEEK_API_BASE', None) if config else None,
            },
        },
        # Generic fallback entry for any model string passed through
        {
            "model_name": "*",
            "litellm_params": {
                "model": "*",
            },
        },
    ]
    
    # Configure Router with minimal, OpenAI-focused settings.
    provider_router = Router(
        model_list=model_list,
        num_retries=3,
    )
    logger.info("Configured LiteLLM Router for OpenAI-compatible provider only")

def _configure_openai_compatible(params: Dict[str, Any], model_name: str, api_key: Optional[str], api_base: Optional[str]) -> None:
    """Configure OpenAI-compatible provider setup."""
    if not model_name.startswith("openai-compatible/"):
        return
    
    # Get config values safely
    config_openai_key = getattr(config, 'OPENAI_COMPATIBLE_API_KEY', None) if config else None
    config_openai_base = getattr(config, 'OPENAI_COMPATIBLE_API_BASE', None) if config else None
    
    # Check if have required config either from parameters or environment
    if (not api_key and not config_openai_key) or (
        not api_base and not config_openai_base
    ):
        raise LLMError(
            "OPENAI_COMPATIBLE_API_KEY and OPENAI_COMPATIBLE_API_BASE is required for openai-compatible models. If just updated the environment variables, wait a few minutes or restart the service to ensure they are loaded."
        )
    
    setup_provider_router(api_key, api_base)
    logger.debug(f"Configured OpenAI-compatible provider with custom API base")

def _add_tools_config(params: Dict[str, Any], tools: Optional[List[Dict[str, Any]]], tool_choice: str) -> None:
    """Add tools configuration to parameters."""
    if tools is None:
        return
    
    params.update({
        "tools": tools,
        "tool_choice": tool_choice
    })
    # logger.debug(f"Added {len(tools)} tools to API parameters")

async def make_llm_api_call(
    messages: List[Dict[str, Any]],
    model_name: str,
    response_format: Optional[Any] = None,
    temperature: float = 0,
    max_tokens: Optional[int] = None,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto",
    api_key: Optional[str] = None,
    api_base: Optional[str] = None,
    stream: bool = True,  # Always stream for better UX
    top_p: Optional[float] = None,
    model_id: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    extra_headers: Optional[Dict[str, str]] = None,
    stop: Optional[List[str]] = None,
) -> Union[Dict[str, Any], AsyncGenerator, ModelResponse]:
    """Make an API call to a language model using LiteLLM.
    
    Args:
        messages: List of message dictionaries
        model_name: Name of the model to use
        response_format: Optional response format specification
        temperature: Temperature for sampling (0-1)
        max_tokens: Maximum tokens to generate
        tools: Optional list of tool definitions
        tool_choice: Tool choice strategy ("auto", "required", "none")
        api_key: Optional API key override
        api_base: Optional API base URL override
        stream: Whether to stream the response
        top_p: Optional top_p for sampling
        model_id: Optional model ID for tracking
        headers: Optional headers to send with request
        extra_headers: Optional extra headers to send with request
        stop: Optional list of stop sequences
    """
    logger.info(f"Making LLM API call to model: {model_name} with {len(messages)} messages")
    
    # Prepare parameters using centralized model configuration
    from core.ai_models import model_manager
    resolved_model_name = model_manager.resolve_model_id(model_name) or model_name
    
    # Only pass headers/extra_headers if they are not None to avoid overriding model config
    override_params = {
        "messages": messages,
        "temperature": temperature,
        "response_format": response_format,
        "top_p": top_p,
        "stream": stream,
        "api_key": api_key,
        "api_base": api_base,
        "stop": stop
    }
    
    # Only add headers if they are provided (not None)
    if headers is not None:
        override_params["headers"] = headers
    if extra_headers is not None:
        override_params["extra_headers"] = extra_headers
    
    params = model_manager.get_litellm_params(resolved_model_name, **override_params)
    
    # Ensure stop sequences are in final params
    if stop is not None:
        params["stop"] = stop
        logger.info(f"🛑 Stop sequences configured: {stop}")
    else:
        params.pop("stop", None)
    
    if model_id:
        params["model_id"] = model_id
    
    if stream:
        params["stream_options"] = {"include_usage": True}
    
    # Apply additional configurations
    _configure_openai_compatible(params, model_name, api_key, api_base)
    _add_tools_config(params, tools, tool_choice)
    
    # Final safeguard: Re-apply stop sequences
    if stop is not None:
        params["stop"] = stop
    
    try:
        # Save debug input if enabled via config
        if config and config.DEBUG_SAVE_LLM_IO:
            try:
                debug_dir = Path("debug_streams")
                debug_dir.mkdir(exist_ok=True)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
                debug_file = debug_dir / f"input_{timestamp}.json"
        
                # Save the exact params going to LiteLLM
                debug_data = {
                    "timestamp": timestamp,
                    "model": params.get("model"),
                    "messages": params.get("messages"),
                    "temperature": params.get("temperature"),
                    "max_tokens": params.get("max_tokens"),
                    "stop": params.get("stop"),
                    "stream": params.get("stream"),
                    "tools": params.get("tools"),
                    "tool_choice": params.get("tool_choice"),
                }
                
                with open(debug_file, 'w', encoding='utf-8') as f:
                    json.dump(debug_data, f, indent=2, ensure_ascii=False)
                    
                logger.info(f"📁 Saved LLM input to: {debug_file}")
            except Exception as e:
                logger.warning(f"⚠️ Error saving debug input: {e}")
        
        response = await provider_router.acompletion(**params)
        
        # For streaming responses, we need to handle errors that occur during iteration
        if hasattr(response, '__aiter__') and stream:
            return _wrap_streaming_response(response)
        
        return response
        
    except Exception as e:
        # Use ErrorProcessor to handle the error consistently
        processed_error = ErrorProcessor.process_llm_error(e, context={"model": model_name})
        ErrorProcessor.log_error(processed_error)
        raise LLMError(processed_error.message)

async def _wrap_streaming_response(response) -> AsyncGenerator:
    """Wrap streaming response to handle errors during iteration."""
    try:
        async for chunk in response:
            yield chunk
    except Exception as e:
        # Convert streaming errors to processed errors
        processed_error = ErrorProcessor.process_llm_error(e)
        ErrorProcessor.log_error(processed_error)
        raise LLMError(processed_error.message)

setup_api_keys()
setup_provider_router()


if __name__ == "__main__":
    from litellm import completion
    import os

    setup_api_keys()

    response = completion(
        model="bedrock/anthropic.claude-sonnet-4-20250115-v1:0",
        messages=[{"role": "user", "content": "Hello! Testing 1M context window."}],
        max_tokens=100,
        extra_headers={
            "anthropic-beta": "context-1m-2025-08-07"  # 👈 Enable 1M context
        }
    )

