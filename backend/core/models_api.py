from fastapi import APIRouter, HTTPException
from typing import List, Dict
from core.utils.config import config

router = APIRouter()


@router.get("/models")
def list_models() -> List[Dict]:
    """
    Return available models based on environment configuration.
    Frontend can call this to render only configured providers.
    """
    try:
        models = []

        # OpenAI (always available if configured)
        openai_key = getattr(config, "OPENAI_API_KEY", None) or getattr(config, "OPENAI_COMPATIBLE_API_KEY", None)
        openai_base = getattr(config, "OPENAI_API_BASE", None) or getattr(config, "OPENAI_COMPATIBLE_API_BASE", None)
        openai_name = getattr(config, "OPENAI_MODEL_NAME", None) or "gpt-4"
        if openai_key or openai_base:
            models.append({
                "id": f"openai/{openai_name}",
                "label": f"OpenAI ({openai_name})",
                "provider": "openai",
                "configured": True,
            })

        # Doubao (通过OpenAI兼容API)
        doubao_key = getattr(config, "DOUBAO_API_KEY", None)
        doubao_base = getattr(config, "DOUBAO_API_BASE", None)
        doubao_name = getattr(config, "DOUBAO_MODEL_NAME", None) or "doubao-seed-1-6-251015"
        if doubao_key or doubao_base:
            models.append({
                "id": f"openai/{doubao_name}",
                "label": f"Doubao ({doubao_name})",
                "provider": "openai",
                "configured": True,
            })
        else:
            # include unconfigured entry (frontend may choose to hide or show disabled)
            models.append({
                "id": f"openai/{doubao_name}",
                "label": f"Doubao ({doubao_name})",
                "provider": "openai",
                "configured": False,
            })

        # theTurbo AI (OpenAI-compatible)
        turbo_key = getattr(config, "THETURBO_API_KEY", None)
        turbo_base = getattr(config, "THETURBO_API_BASE", None)
        turbo_name = getattr(config, "THETURBO_MODEL_NAME", None) or "gpt-5.1"
        if turbo_key or turbo_base:
            models.append({
                "id": f"theturbo/{turbo_name}",
                "label": f"theTurbo ({turbo_name})",
                "provider": "theturbo",
                "configured": True,
            })
        else:
            models.append({
                "id": f"theturbo/{turbo_name}",
                "label": f"theTurbo ({turbo_name})",
                "provider": "theturbo",
                "configured": False,
            })

        return models
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


