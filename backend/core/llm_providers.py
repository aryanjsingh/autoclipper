"""
Multi-model Provider Unified Interface
Supports OpenAI, Gemini, SiliconFlow, Alibaba DashScope, etc.
"""
import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
from pathlib import Path

from .kiro_gateway import (
    DEFAULT_MODEL as DEFAULT_KIRO_MODEL,
    get_gateway_api_key,
    get_gateway_base_url,
)

logger = logging.getLogger(__name__)

class ProviderType(Enum):
    """Model provider type"""
    DASHSCOPE = "dashscope"  # Alibaba Tongyi Qianwen
    OPENAI = "openai"        # OpenAI
    GEMINI = "gemini"        # Google Gemini
    SILICONFLOW = "siliconflow"  # SiliconFlow
    KIRO = "kiro"            # Kiro Gateway

@dataclass
class ModelInfo:
    """Model information"""
    name: str
    display_name: str
    provider: ProviderType
    max_tokens: int
    cost_per_token: Optional[float] = None
    description: Optional[str] = None

@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    usage: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    finish_reason: Optional[str] = None

class LLMProvider(ABC):
    """LLM provider abstract base class"""
    
    def __init__(self, api_key: str, model_name: str, **kwargs):
        self.api_key = api_key
        self.model_name = model_name
        self.kwargs = kwargs
    
    @abstractmethod
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        """
        Call model API
        
        Args:
            prompt: Prompt text
            input_data: Input data
            **kwargs: Additional parameters
            
        Returns:
            LLMResponse: Model response
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test API connection
        
        Returns:
            bool: Whether connection is successful
        """
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """
        Get available model list
        
        Returns:
            List[ModelInfo]: Available model list
        """
        pass
    
    def _build_full_input(self, prompt: str, input_data: Any = None) -> str:
        """Build complete input"""
        if input_data:
            if isinstance(input_data, dict):
                return f"{prompt}\n\nInput content:\n{json.dumps(input_data, ensure_ascii=False, indent=2)}"
            else:
                return f"{prompt}\n\nInput content:\n{input_data}"
        return prompt

class DashScopeProvider(LLMProvider):
    """Alibaba DashScope provider"""
    
    def __init__(self, api_key: str, model_name: str = "qwen-plus", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        try:
            from dashscope import Generation
            self.generation = Generation
        except ImportError:
            raise ImportError("Please install dashscope: pip install dashscope")
    
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        """Call DashScope API"""
        try:
            full_input = self._build_full_input(prompt, input_data)
            
            response_or_gen = self.generation.call(
                model=self.model_name,
                prompt=full_input,
                api_key=self.api_key,
                stream=False,
                **kwargs
            )
            
            # Handle response
            # DashScope's GenerationResponse has __iter__ method but is not a real iterator
            # Use the response object directly
            response = response_or_gen
            
            if response and response.status_code == 200:
                if response.output and response.output.text is not None:
                    return LLMResponse(
                        content=response.output.text,
                        model=self.model_name,
                        finish_reason=getattr(response.output, 'finish_reason', None)
                    )
                else:
                    finish_reason = getattr(response.output, 'finish_reason', 'unknown') if response.output else 'unknown'
                    logger.warning(f"API request succeeded, but output is empty. Finish reason: {finish_reason}")
                    return LLMResponse(content="")
            else:
                code = getattr(response, 'code', 'N/A')
                message = getattr(response, 'message', 'Unknown API error')
                raise Exception(f"API call failed - Status: {response.status_code}, Code: {code}, Message: {message}")
                
        except Exception as e:
            logger.error(f"DashScope call failed: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test DashScope connection"""
        try:
            response = self.call("Please reply with 'Test successful'")
            return "Test successful" in response.content or "success" in response.content.lower()
        except Exception as e:
            logger.error(f"DashScope connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get available DashScope models"""
        return [
            ModelInfo(
                name="qwen-plus",
                display_name="Tongyi Qianwen Plus",
                provider=ProviderType.DASHSCOPE,
                max_tokens=8192,
                description="Alibaba Cloud Tongyi Qianwen Plus model"
            ),
            ModelInfo(
                name="qwen-max",
                display_name="Tongyi Qianwen Max",
                provider=ProviderType.DASHSCOPE,
                max_tokens=8192,
                description="Alibaba Cloud Tongyi Qianwen Max model"
            ),
            ModelInfo(
                name="qwen-turbo",
                display_name="Tongyi Qianwen Turbo",
                provider=ProviderType.DASHSCOPE,
                max_tokens=8192,
                description="Alibaba Cloud Tongyi Qianwen Turbo model"
            )
        ]

class OpenAIProvider(LLMProvider):
    """OpenAI provider"""
    
    def __init__(self, api_key: str, model_name: str = "gpt-3.5-turbo", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        try:
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("Please install openai: pip install openai")
    
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        """Call OpenAI API"""
        try:
            full_input = self._build_full_input(prompt, input_data)
            
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": full_input}],
                **kwargs
            )
            
            content = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            } if response.usage else None
            
            return LLMResponse(
                content=content,
                usage=usage,
                model=self.model_name,
                finish_reason=response.choices[0].finish_reason
            )
            
        except Exception as e:
            logger.error(f"OpenAI call failed: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test OpenAI connection"""
        try:
            response = self.call("Please reply with 'Test successful'")
            return "Test successful" in response.content or "success" in response.content.lower()
        except Exception as e:
            logger.error(f"OpenAI connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get available OpenAI models"""
        return [
            ModelInfo(
                name="gpt-3.5-turbo",
                display_name="GPT-3.5 Turbo",
                provider=ProviderType.OPENAI,
                max_tokens=4096,
                description="OpenAI GPT-3.5 Turbo model"
            ),
            ModelInfo(
                name="gpt-4",
                display_name="GPT-4",
                provider=ProviderType.OPENAI,
                max_tokens=8192,
                description="OpenAI GPT-4 model"
            ),
            ModelInfo(
                name="gpt-4-turbo",
                display_name="GPT-4 Turbo",
                provider=ProviderType.OPENAI,
                max_tokens=128000,
                description="OpenAI GPT-4 Turbo model"
            )
        ]

class GeminiProvider(LLMProvider):
    """Google Gemini provider"""
    
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
        except ImportError:
            raise ImportError("Please install google-generativeai: pip install google-generativeai")
    
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        """Call Gemini API"""
        try:
            full_input = self._build_full_input(prompt, input_data)
            
            response = self.model.generate_content(full_input, **kwargs)
            
            return LLMResponse(
                content=response.text,
                model=self.model_name,
                finish_reason=getattr(response, 'finish_reason', None)
            )
            
        except Exception as e:
            logger.error(f"Gemini call failed: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test Gemini connection"""
        try:
            response = self.call("Please reply with 'Test successful'")
            return "Test successful" in response.content or "success" in response.content.lower()
        except Exception as e:
            logger.error(f"Gemini connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get available Gemini models"""
        return [
            ModelInfo(
                name="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash",
                provider=ProviderType.GEMINI,
                max_tokens=1000000,
                description="Google Gemini 2.5 Flash model"
            ),
            ModelInfo(
                name="gemini-1.5-pro",
                display_name="Gemini 1.5 Pro",
                provider=ProviderType.GEMINI,
                max_tokens=2000000,
                description="Google Gemini 1.5 Pro model"
            ),
            ModelInfo(
                name="gemini-1.5-flash",
                display_name="Gemini 1.5 Flash",
                provider=ProviderType.GEMINI,
                max_tokens=1000000,
                description="Google Gemini 1.5 Flash model"
            )
        ]

class SiliconFlowProvider(LLMProvider):
    """SiliconFlow provider"""
    
    def __init__(self, api_key: str, model_name: str = "Qwen/Qwen2.5-7B-Instruct", **kwargs):
        super().__init__(api_key, model_name, **kwargs)
        self.base_url = "https://api.siliconflow.cn/v1"
    
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        """Call SiliconFlow API"""
        try:
            import requests
            
            full_input = self._build_full_input(prompt, input_data)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": full_input}],
                "stream": False,
                **kwargs
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage")
            
            return LLMResponse(
                content=content,
                usage=usage,
                model=self.model_name,
                finish_reason=result["choices"][0].get("finish_reason")
            )
            
        except Exception as e:
            logger.error(f"SiliconFlow call failed: {str(e)}")
            raise
    
    def test_connection(self) -> bool:
        """Test SiliconFlow connection"""
        try:
            response = self.call("Please reply with 'Test successful'")
            return "Test successful" in response.content or "success" in response.content.lower()
        except Exception as e:
            logger.error(f"SiliconFlow connection test failed: {e}")
            return False
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get available SiliconFlow models"""
        return [
            ModelInfo(
                name="Qwen/Qwen2.5-7B-Instruct",
                display_name="Qwen2.5-7B",
                provider=ProviderType.SILICONFLOW,
                max_tokens=32768,
                description="SiliconFlow Qwen2.5-7B model"
            ),
            ModelInfo(
                name="Qwen/Qwen2.5-14B-Instruct",
                display_name="Qwen2.5-14B",
                provider=ProviderType.SILICONFLOW,
                max_tokens=32768,
                description="SiliconFlow Qwen2.5-14B model"
            ),
            ModelInfo(
                name="Qwen/Qwen2.5-32B-Instruct",
                display_name="Qwen2.5-32B",
                provider=ProviderType.SILICONFLOW,
                max_tokens=32768,
                description="SiliconFlow Qwen2.5-32B model"
            ),
            ModelInfo(
                name="deepseek-ai/DeepSeek-V2.5",
                display_name="DeepSeek-V2.5",
                provider=ProviderType.SILICONFLOW,
                max_tokens=65536,
                description="SiliconFlow DeepSeek-V2.5 model"
            )
        ]

class KiroGatewayProvider(LLMProvider):
    """Kiro Gateway provider using its OpenAI-compatible API."""

    def __init__(self, api_key: str = "", model_name: str = DEFAULT_KIRO_MODEL, **kwargs):
        super().__init__(api_key, model_name or DEFAULT_KIRO_MODEL, **kwargs)
        self.api_key = get_gateway_api_key(api_key)
        self.base_url = get_gateway_base_url(kwargs.get("base_url"))
        default_timeout = int(os.environ.get("KIRO_GATEWAY_TIMEOUT", "900"))
        self.timeout = int(kwargs.get("timeout", default_timeout))

        if not self.api_key:
            raise ValueError(
                "Kiro Gateway API key not found. Please set KIRO_GATEWAY_API_KEY, "
                "or configure PROXY_API_KEY in ../kiro-gateway/.env"
            )

    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        """Call Kiro Gateway through /v1/chat/completions."""
        try:
            import requests

            full_input = self._build_full_input(prompt, input_data)
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": full_input}],
                "stream": False,
            }

            passthrough_keys = {
                "temperature",
                "top_p",
                "max_tokens",
                "presence_penalty",
                "frequency_penalty",
                "stop",
            }
            payload.update({key: value for key, value in kwargs.items() if key in passthrough_keys})

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout,
            )

            if response.status_code >= 400:
                error_message = response.text
                try:
                    error_json = response.json()
                    error_message = error_json.get("error", {}).get("message") or error_message
                except Exception:
                    pass
                raise Exception(f"Kiro Gateway call failed - Status: {response.status_code}, Message: {error_message}")

            result = response.json()
            choice = result["choices"][0]
            message = choice.get("message", {})
            content = message.get("content") or ""

            return LLMResponse(
                content=content,
                usage=result.get("usage"),
                model=result.get("model", self.model_name),
                finish_reason=choice.get("finish_reason"),
            )

        except Exception as e:
            logger.error(f"Kiro Gateway call failed: {str(e)}")
            raise

    def test_connection(self) -> bool:
        """Test Kiro Gateway connectivity."""
        try:
            response = self.call("Please reply with 'Test successful'")
            return "Test successful" in response.content or "success" in response.content.lower()
        except Exception as e:
            logger.error(f"Kiro Gateway connection test failed: {e}")
            return False

    def get_available_models(self) -> List[ModelInfo]:
        """Return common Kiro Gateway model aliases."""
        return [
            ModelInfo(
                name="claude-opus-4.8",
                display_name="Claude Opus 4.8",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway latest high-quality Opus model (default)"
            ),
            ModelInfo(
                name="claude-opus-4.7",
                display_name="Claude Opus 4.7",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway Opus 4.7"
            ),
            ModelInfo(
                name="claude-sonnet-4-5",
                display_name="Claude Sonnet 4.5",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway default high-quality model"
            ),
            ModelInfo(
                name="claude-haiku-4-5",
                display_name="Claude Haiku 4.5",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway fast model"
            ),
            ModelInfo(
                name="claude-sonnet-4",
                display_name="Claude Sonnet 4",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway Claude Sonnet 4"
            ),
            ModelInfo(
                name="glm-5",
                display_name="GLM-5",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway GLM-5"
            ),
            ModelInfo(
                name="deepseek-v3-2",
                display_name="DeepSeek-V3.2",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway DeepSeek-V3.2"
            ),
            ModelInfo(
                name="minimax-m2-5",
                display_name="MiniMax M2.5",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway MiniMax M2.5"
            ),
            ModelInfo(
                name="minimax-m2-1",
                display_name="MiniMax M2.1",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway MiniMax M2.1"
            ),
            ModelInfo(
                name="qwen3-coder-next",
                display_name="Qwen3-Coder-Next",
                provider=ProviderType.KIRO,
                max_tokens=200000,
                description="Kiro Gateway Qwen3 Coder"
            )
        ]

class LLMProviderFactory:
    """LLM provider factory"""
    
    _providers = {
        ProviderType.DASHSCOPE: DashScopeProvider,
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.SILICONFLOW: SiliconFlowProvider,
        ProviderType.KIRO: KiroGatewayProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_type: ProviderType, api_key: str, model_name: str, **kwargs) -> LLMProvider:
        """Create provider instance"""
        if provider_type not in cls._providers:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        provider_class = cls._providers[provider_type]
        return provider_class(api_key, model_name, **kwargs)
    
    @classmethod
    def get_all_available_models(cls) -> Dict[ProviderType, List[ModelInfo]]:
        """Get available models from all providers"""
        models = {}
        for provider_type, provider_class in cls._providers.items():
            try:
                # Create temporary instance to get model list
                temp_provider = provider_class("dummy_key", "dummy_model")
                models[provider_type] = temp_provider.get_available_models()
            except Exception as e:
                logger.warning(f"Unable to get model list for {provider_type.value}: {e}")
                models[provider_type] = []
        return models
