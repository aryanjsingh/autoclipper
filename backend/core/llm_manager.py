"""
LLM Manager - Unified management of multiple model providers
"""
import json
import logging
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

from .llm_providers import (
    LLMProvider, LLMProviderFactory, ProviderType, 
    ModelInfo, LLMResponse
)
from .kiro_gateway import (
    DEFAULT_MODEL as DEFAULT_KIRO_MODEL,
    KIRO_MODEL_OPUS,
    KIRO_MODEL_SONNET,
    get_gateway_api_key,
    model_for_pipeline_step,
)

logger = logging.getLogger(__name__)

class LLMManager:
    """LLM Manager"""
    
    def __init__(self, settings_file: Optional[Path] = None):
        self.settings_file = settings_file or self._get_default_settings_file()
        self.current_provider: Optional[LLMProvider] = None
        self.settings = self._load_settings()
        self._initialize_provider()
    
    def _get_default_settings_file(self) -> Path:
        """Get default settings file path"""
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent  # backend/core -> backend -> project_root
        return project_root / "data" / "settings.json"
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load settings"""
        default_settings = {
            "llm_provider": "kiro",
            "dashscope_api_key": "",
            "openai_api_key": "",
            "gemini_api_key": "",
            "siliconflow_api_key": "",
            "kiro_api_key": "",
            "kiro_base_url": "",
            "model_name": DEFAULT_KIRO_MODEL,
            "kiro_model_sonnet": KIRO_MODEL_SONNET,
            "chunk_size": 5000,
            "min_score_threshold": 0.7,
            "max_clips_per_collection": 5,
            "kiro_connect_timeout_seconds": 5,
            "kiro_read_timeout_seconds": 0,
            "kiro_max_tokens": 65536,
            "llm_retry_delay_seconds": 0,
        }
        
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    saved_settings = json.load(f)
                    default_settings.update(saved_settings)
            except Exception as e:
                logger.warning(f"Failed to load settings file: {e}")

        if (
            default_settings.get("llm_provider") == ProviderType.KIRO.value
            and default_settings.get("model_name") == "qwen-plus"
        ):
            default_settings["model_name"] = DEFAULT_KIRO_MODEL
        
        return default_settings
    
    def _save_settings(self):
        """Save settings"""
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            raise
    
    def _initialize_provider(self):
        """Initialize current provider"""
        try:
            provider_type = ProviderType(self.settings.get("llm_provider", "dashscope"))
            model_name = self.settings.get("model_name", "qwen-plus")
            
            # Get API key for the corresponding provider
            api_key = self._get_api_key_for_provider(provider_type)
            
            if api_key or provider_type == ProviderType.KIRO:
                provider_kwargs = {}
                if provider_type == ProviderType.KIRO:
                    provider_kwargs.update(self._kiro_provider_kwargs())

                self.current_provider = LLMProviderFactory.create_provider(
                    provider_type, api_key, model_name, **provider_kwargs
                )
                logger.info(f"Initialized {provider_type.value} provider, model: {model_name}")
            else:
                logger.warning(f"API key not found for {provider_type.value}")
                
        except Exception as e:
            logger.error(f"Failed to initialize provider: {e}")
            self.current_provider = None
    
    def _kiro_provider_kwargs(self) -> Dict[str, Any]:
        """Kiro HTTP: short connect timeout, no read cap (0 = unlimited)."""
        read_raw = self.settings.get("kiro_read_timeout_seconds", 0)
        read_timeout = None if int(read_raw or 0) <= 0 else int(read_raw)
        return {
            "base_url": self.settings.get("kiro_base_url", ""),
            "connect_timeout": int(self.settings.get("kiro_connect_timeout_seconds", 5)),
            "timeout": read_timeout,
        }

    def _get_api_key_for_provider(self, provider_type: ProviderType) -> Optional[str]:
        """Get API key for specified provider"""
        key_mapping = {
            ProviderType.DASHSCOPE: "dashscope_api_key",
            ProviderType.OPENAI: "openai_api_key",
            ProviderType.GEMINI: "gemini_api_key",
            ProviderType.SILICONFLOW: "siliconflow_api_key",
            ProviderType.KIRO: "kiro_api_key",
        }
        
        key_name = key_mapping.get(provider_type)
        if key_name:
            if provider_type == ProviderType.KIRO:
                return get_gateway_api_key(self.settings.get(key_name, ""))
            return self.settings.get(key_name, "")
        return None
    
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update settings"""
        self.settings.update(new_settings)
        self._save_settings()
        self._initialize_provider()
    
    def set_provider(self, provider_type: ProviderType, api_key: str, model_name: str):
        """Set provider"""
        try:
            # Update settings
            provider_settings = {
                "llm_provider": provider_type.value,
                "model_name": model_name
            }
            
            # Update API key for the corresponding provider
            key_mapping = {
                ProviderType.DASHSCOPE: "dashscope_api_key",
                ProviderType.OPENAI: "openai_api_key",
                ProviderType.GEMINI: "gemini_api_key",
                ProviderType.SILICONFLOW: "siliconflow_api_key",
                ProviderType.KIRO: "kiro_api_key",
            }
            
            key_name = key_mapping.get(provider_type)
            if key_name:
                provider_settings[key_name] = api_key
            
            self.update_settings(provider_settings)
            
            # Create new provider instance
            provider_kwargs = {}
            if provider_type == ProviderType.KIRO:
                provider_kwargs.update(self._kiro_provider_kwargs())

            self.current_provider = LLMProviderFactory.create_provider(
                provider_type, api_key, model_name, **provider_kwargs
            )
            
            logger.info(f"Switched to {provider_type.value} provider, model: {model_name}")
            
        except Exception as e:
            logger.error(f"Failed to set provider: {e}")
            raise
    
    def model_for_pipeline_step(self, step: str) -> str:
        return model_for_pipeline_step(step, self.settings)

    def call(self, prompt: str, input_data: Any = None, model: Optional[str] = None, **kwargs) -> str:
        """Call LLM"""
        if not self.current_provider:
            raise ValueError("LLM provider not configured. Please configure API key in the settings page.")
        
        if model:
            kwargs["model"] = model
        kwargs = self._with_provider_defaults(**kwargs)
        used_model = kwargs.get("model", self.settings.get("model_name"))
        logger.info("LLM call model=%s", used_model)
        try:
            response = self.current_provider.call(prompt, input_data, **kwargs)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
    
    def _with_provider_defaults(self, **kwargs) -> Dict[str, Any]:
        """Apply provider-specific defaults (output budget, etc.)."""
        out = dict(kwargs)
        if self.settings.get("llm_provider") == "kiro":
            if "max_tokens" not in out:
                out["max_tokens"] = int(self.settings.get("kiro_max_tokens", 65536))
        return out

    def call_with_retry(
        self,
        prompt: str,
        input_data: Any = None,
        max_retries: int = 3,
        model: Optional[str] = None,
        **kwargs,
    ) -> str:
        """LLM call with retry mechanism (no backoff delay by default)."""
        retry_delay = float(self.settings.get("llm_retry_delay_seconds", 0))
        for attempt in range(max_retries):
            try:
                return self.call(prompt, input_data, model=model, **kwargs)
            except ValueError:  # If API key or parameter error, do not retry
                raise
            except Exception as e:
                if attempt == max_retries - 1:
                    logger.error(f"LLM call failed completely after {max_retries} retries.")
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, preparing to retry: {str(e)}")
                if retry_delay > 0:
                    import time
                    time.sleep(retry_delay)
        return ""
    
    def test_provider_connection(self, provider_type: ProviderType, api_key: str, model_name: str) -> bool:
        """Test provider connection"""
        try:
            provider = LLMProviderFactory.create_provider(provider_type, api_key, model_name)
            return provider.test_connection()
        except Exception as e:
            logger.error(f"Failed to test {provider_type.value} connection: {e}")
            return False
    
    def get_current_provider_info(self) -> Dict[str, Any]:
        """Get current provider information"""
        if not self.current_provider:
            return {"provider": None, "model": None, "available": False}
        
        provider_type = ProviderType(self.settings.get("llm_provider", "dashscope"))
        model_name = self.settings.get("model_name", "qwen-plus")
        
        return {
            "provider": provider_type.value,
            "model": model_name,
            "available": True,
            "display_name": self._get_provider_display_name(provider_type)
        }
    
    def _get_provider_display_name(self, provider_type: ProviderType) -> str:
        """Get provider display name"""
        display_names = {
            ProviderType.DASHSCOPE: "Alibaba Tongyi Qianwen",
            ProviderType.OPENAI: "OpenAI",
            ProviderType.GEMINI: "Google Gemini",
            ProviderType.SILICONFLOW: "SiliconFlow",
            ProviderType.KIRO: "Kiro Gateway"
        }
        return display_names.get(provider_type, provider_type.value)
    
    def get_all_available_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all available models"""
        all_models = LLMProviderFactory.get_all_available_models()
        result = {}
        
        for provider_type, models in all_models.items():
            provider_name = provider_type.value
            result[provider_name] = [
                {
                    "name": model.name,
                    "display_name": model.display_name,
                    "max_tokens": model.max_tokens,
                    "description": model.description
                }
                for model in models
            ]
        
        return result
    
    def parse_json_response(self, response: str) -> Any:
        """Parse JSON response (maintains compatibility with original LLMClient)"""
        if not self.current_provider:
            raise ValueError("LLM provider not configured")
        
        # This can reuse the original LLMClient's JSON parsing logic
        # For compatibility, we create a temporary LLMClient instance
        from ..utils.llm_client import LLMClient
        temp_client = LLMClient()
        return temp_client.parse_json_response(response)

# Global LLM manager instance
_llm_manager: Optional[LLMManager] = None

def get_llm_manager() -> LLMManager:
    """Get global LLM manager instance"""
    global _llm_manager
    if _llm_manager is None:
        _llm_manager = LLMManager()
    return _llm_manager

def initialize_llm_manager(settings_file: Optional[Path] = None) -> LLMManager:
    """Initialize LLM manager"""
    global _llm_manager
    _llm_manager = LLMManager(settings_file)
    return _llm_manager
