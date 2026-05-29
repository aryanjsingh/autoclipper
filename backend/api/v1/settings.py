"""
Settings API routes
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import json
from pathlib import Path

router = APIRouter()

class SettingsRequest(BaseModel):
    """Settings request model"""
    # Multi-provider support
    llm_provider: Optional[str] = None
    dashscope_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    siliconflow_api_key: Optional[str] = None
    kiro_api_key: Optional[str] = None
    kiro_base_url: Optional[str] = None
    model_name: Optional[str] = None
    chunk_size: Optional[int] = None
    min_score_threshold: Optional[float] = None
    max_clips_per_collection: Optional[int] = None

class ApiKeyTestRequest(BaseModel):
    """API key test request"""
    provider: str
    api_key: str
    model_name: str

class ApiKeyTestResponse(BaseModel):
    """API key test response"""
    success: bool
    error: Optional[str] = None

def get_settings_file_path() -> Path:
    """Get settings file path"""
    from ...core.path_utils import get_settings_file_path as get_settings_path
    return get_settings_path()

def load_settings() -> Dict[str, Any]:
    """Load settings"""
    settings_file = get_settings_file_path()
    default_settings = {
        "llm_provider": "kiro",
        "dashscope_api_key": "",
        "openai_api_key": "",
        "gemini_api_key": "",
        "siliconflow_api_key": "",
        "kiro_api_key": "",
        "kiro_base_url": "",
        "model_name": "claude-sonnet-4-5",
        "chunk_size": 5000,
        "min_score_threshold": 0.7,
        "max_clips_per_collection": 5
    }
    
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
                # Merge default settings with saved settings
                default_settings.update(saved_settings)
        except Exception as e:
            print(f"Failed to load settings file: {e}")

    if default_settings.get("llm_provider") == "kiro" and default_settings.get("model_name") == "qwen-plus":
        default_settings["model_name"] = "claude-sonnet-4-5"
    
    return default_settings

def save_settings(settings: Dict[str, Any]):
    """Save settings"""
    settings_file = get_settings_file_path()
    settings_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save settings: {e}")

@router.get("/")
async def get_settings():
    """Get system settings"""
    try:
        settings = load_settings()
        # Return full settings without hiding API keys
        return settings
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {e}")

@router.post("/")
async def update_settings(request: SettingsRequest):
    """Update system settings"""
    try:
        settings = load_settings()
        
        # Update multi-provider settings
        if request.llm_provider is not None:
            settings["llm_provider"] = request.llm_provider
        
        if request.dashscope_api_key is not None:
            settings["dashscope_api_key"] = request.dashscope_api_key
            # Also set environment variable for backward compatibility
            os.environ["DASHSCOPE_API_KEY"] = request.dashscope_api_key
        
        if request.openai_api_key is not None:
            settings["openai_api_key"] = request.openai_api_key
        
        if request.gemini_api_key is not None:
            settings["gemini_api_key"] = request.gemini_api_key
        
        if request.siliconflow_api_key is not None:
            settings["siliconflow_api_key"] = request.siliconflow_api_key

        if request.kiro_api_key is not None:
            settings["kiro_api_key"] = request.kiro_api_key
            if request.kiro_api_key:
                os.environ["KIRO_GATEWAY_API_KEY"] = request.kiro_api_key

        if request.kiro_base_url is not None:
            settings["kiro_base_url"] = request.kiro_base_url
            if request.kiro_base_url:
                os.environ["KIRO_GATEWAY_BASE_URL"] = request.kiro_base_url
        
        if request.model_name is not None:
            settings["model_name"] = request.model_name
        
        if request.chunk_size is not None:
            settings["chunk_size"] = request.chunk_size
        
        if request.min_score_threshold is not None:
            settings["min_score_threshold"] = request.min_score_threshold
        
        if request.max_clips_per_collection is not None:
            settings["max_clips_per_collection"] = request.max_clips_per_collection
        
        # Save settings
        save_settings(settings)
        
        # Update LLM manager
        try:
            from ...core.llm_manager import get_llm_manager
            llm_manager = get_llm_manager()
            llm_manager.update_settings(settings)
        except Exception as e:
            print(f"Failed to update LLM manager: {e}")
        
        return {"message": "Settings updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {e}")

@router.post("/test-api-key")
async def test_api_key(request: ApiKeyTestRequest) -> ApiKeyTestResponse:
    """Test API key"""
    try:
        # Import LLM manager
        from ...core.llm_manager import get_llm_manager
        from ...core.llm_providers import ProviderType
        
        # Validate provider type
        try:
            provider_type = ProviderType(request.provider)
        except ValueError:
            return ApiKeyTestResponse(success=False, error=f"Unsupported provider type: {request.provider}")
        
        # Test connection
        llm_manager = get_llm_manager()
        success = llm_manager.test_provider_connection(provider_type, request.api_key, request.model_name)
        
        if success:
            return ApiKeyTestResponse(success=True)
        else:
            return ApiKeyTestResponse(success=False, error="API connection test failed")
                
    except Exception as e:
        return ApiKeyTestResponse(success=False, error=str(e))

@router.get("/available-models")
async def get_available_models():
    """Get all available models"""
    try:
        from ...core.llm_manager import get_llm_manager
        llm_manager = get_llm_manager()
        return llm_manager.get_all_available_models()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get available models: {e}")

@router.get("/current-provider")
async def get_current_provider():
    """Get current provider info"""
    try:
        from ...core.llm_manager import get_llm_manager
        llm_manager = get_llm_manager()
        return llm_manager.get_current_provider_info()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get current provider info: {e}") 
