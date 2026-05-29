"""
Speech recognition API endpoint
Provides speech recognition configuration management and status query functionality
"""
import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path

from ...utils.speech_recognizer import (
    get_available_speech_recognition_methods,
    get_supported_languages,
    get_whisper_models,
    SpeechRecognitionConfig,
    SpeechRecognitionMethod,
    LanguageCode
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/speech-recognition", tags=["Speech Recognition"])


class SpeechRecognitionStatus(BaseModel):
    """Speech recognition status"""
    available_methods: Dict[str, bool]
    supported_languages: List[str]
    whisper_models: List[str]
    default_config: Dict[str, Any]
    
    class Config:
        arbitrary_types_allowed = True


class SpeechRecognitionRequest(BaseModel):
    """Speech recognition request"""
    method: str
    language: str = "auto"
    model: str = "base"
    timeout: int = 300
    output_format: str = "srt"
    enable_timestamps: bool = True
    enable_punctuation: bool = True
    enable_speaker_diarization: bool = False


@router.get("/status", response_model=SpeechRecognitionStatus)
async def get_speech_recognition_status():
    """Get speech recognition status"""
    try:
        available_methods = get_available_speech_recognition_methods()
        supported_languages = get_supported_languages()
        whisper_models = get_whisper_models()
        
        # Default configuration
        default_config = SpeechRecognitionConfig().__dict__
        # Convert enums to strings
        default_config["method"] = default_config["method"].value
        default_config["language"] = default_config["language"].value
        
        return SpeechRecognitionStatus(
            available_methods=available_methods,
            supported_languages=supported_languages,
            whisper_models=whisper_models,
            default_config=default_config
        )
    except Exception as e:
        logger.error(f"Failed to get speech recognition status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get speech recognition status: {e}")


@router.get("/methods")
async def get_available_methods():
    """Get available speech recognition methods"""
    try:
        return get_available_speech_recognition_methods()
    except Exception as e:
        logger.error(f"Failed to get available methods: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available methods: {e}")


@router.get("/languages")
async def get_supported_languages_list():
    """Get list of supported languages"""
    try:
        return get_supported_languages()
    except Exception as e:
        logger.error(f"Failed to get supported languages: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supported languages: {e}")


@router.get("/whisper-models")
async def get_whisper_models_list():
    """Get list of available Whisper models"""
    try:
        return get_whisper_models()
    except Exception as e:
        logger.error(f"Failed to get Whisper models: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get Whisper models: {e}")


@router.post("/test")
async def test_speech_recognition(request: SpeechRecognitionRequest):
    """Test speech recognition configuration"""
    try:
        # Validate method availability
        available_methods = get_available_speech_recognition_methods()
        if not available_methods.get(request.method, False):
            raise HTTPException(
                status_code=400, 
                detail=f"Speech recognition method '{request.method}' is not available"
            )
        
        # Validate language support
        supported_languages = get_supported_languages()
        if request.language not in supported_languages:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}"
            )
        
        # Validate Whisper model (if using whisper)
        if request.method == "whisper_local":
            whisper_models = get_whisper_models()
            if request.model not in whisper_models:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported Whisper model: {request.model}"
                )
        
        return {
            "status": "success",
            "message": "Speech recognition configuration validation passed",
            "config": request.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to test speech recognition configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test speech recognition configuration: {e}")


@router.get("/install-guide")
async def get_install_guide(method: str = Query(..., description="Speech recognition method")):
    """Get installation guide"""
    guides = {
        "whisper_local": {
            "title": "Local Whisper Installation Guide",
            "description": "Install local Whisper speech recognition tool",
            "steps": [
                "1. Install Python dependencies: pip install openai-whisper",
                "2. Install system dependencies:",
                "   - Ubuntu/Debian: sudo apt install ffmpeg",
                "   - macOS: brew install ffmpeg",
                "   - Windows: Download ffmpeg and add to PATH",
                "3. Verify installation: whisper --help",
                "4. Optional: Install PyTorch GPU support for better performance"
            ],
            "notes": [
                "Whisper supports multiple model sizes: tiny(39MB), base(74MB), small(244MB), medium(769MB), large(1550MB)",
                "Larger models have higher accuracy but slower processing speed",
                "Model files will be automatically downloaded on first use"
            ]
        },
        "openai_api": {
            "title": "OpenAI API Configuration Guide",
            "description": "Configure OpenAI API speech recognition",
            "steps": [
                "1. Register OpenAI account and get API key",
                "2. Set environment variable: export OPENAI_API_KEY='your-api-key'",
                "3. Or set API key in configuration file"
            ],
            "notes": [
                "Requires network connection",
                "Has API call costs",
                "Higher accuracy"
            ]
        },
        "azure_speech": {
            "title": "Azure Speech Services Configuration Guide",
            "description": "Configure Azure Speech Services",
            "steps": [
                "1. Create Azure account and enable Speech Services",
                "2. Get API key and region information",
                "3. Set environment variables:",
                "   export AZURE_SPEECH_KEY='your-api-key'",
                "   export AZURE_SPEECH_REGION='your-region'"
            ],
            "notes": [
                "Requires Azure account",
                "Has API call costs",
                "Supports multiple languages and features"
            ]
        },
        "google_speech": {
            "title": "Google Speech-to-Text Configuration Guide",
            "description": "Configure Google Speech-to-Text",
            "steps": [
                "1. Create Google Cloud project",
                "2. Enable Speech-to-Text API",
                "3. Create service account and download credentials file",
                "4. Set environment variable: export GOOGLE_APPLICATION_CREDENTIALS='path/to/credentials.json'"
            ],
            "notes": [
                "Requires Google Cloud account",
                "Has API call costs",
                "Supports multiple languages and advanced features"
            ]
        },
        "aliyun_speech": {
            "title": "Alibaba Cloud Speech Recognition Configuration Guide",
            "description": "Configure Alibaba Cloud speech recognition",
            "steps": [
                "1. Register Alibaba Cloud account",
                "2. Enable intelligent speech interaction service",
                "3. Create AccessKey and AppKey",
                "4. Set environment variables:",
                "   export ALIYUN_ACCESS_KEY_ID='your-access-key'",
                "   export ALIYUN_ACCESS_KEY_SECRET='your-secret-key'",
                "   export ALIYUN_SPEECH_APP_KEY='your-app-key'"
            ],
            "notes": [
                "Requires Alibaba Cloud account",
                "Has API call costs",
                "Better Chinese recognition performance"
            ]
        }
    }
    
    if method not in guides:
        raise HTTPException(status_code=400, detail=f"Unsupported speech recognition method: {method}")
    
    return guides[method]
