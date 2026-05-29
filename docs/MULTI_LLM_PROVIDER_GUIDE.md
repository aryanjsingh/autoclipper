# Multi-model provider access guide
## 🎯 Function Overview
The system now supports multiple AI model providers, and users can choose different service providers and models according to their needs to achieve a more flexible AI automatic slicing function.
## 🏗️ Architecture design
### Supported providers
| Provider | Display Name | Main Model | Features ||--------|----------|----------|------|
| `dashscope` | Alibaba Tongyi Qianwen | qwen-plus, qwen-max, qwen-turbo | Stable domestic access, good Chinese understanding || `openai` | OpenAI | gpt-3.5-turbo, gpt-4, gpt-4-turbo | Globally leading, powerful || `gemini` | Google Gemini | gemini-2.5-flash, gemini-1.5-pro | Multi-modal support, long context || `siliconflow` | Silicon-based flow | Qwen2.5 series, DeepSeek-V2.5 | High cost performance, localized |
### System architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Settings Page                   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Provider   │  │  API Key    │  │   Model     │         │
│  │  Selection  │  │   Input     │  │  Selection  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   Backend API Service                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Settings   │  │ Connection  │  │    Model    │         │
│  │  Mgmt API   │  │  Test API   │  │  Query API  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   LLM Manager                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Provider   │  │  Unified    │  │  Config     │         │
│  │  Factory    │  │  Interface  │  │  Management │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                   Provider Implementations                  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ DashScope   │  │   OpenAI    │  │   Gemini    │         │
│  │  Provider   │  │  Provider   │  │  Provider   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│  ┌─────────────┐                                           │
│  │SiliconFlow  │                                           │
│  │  Provider   │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick start
### 1. Install dependencies
```bash
# Run dependency installation script
python install_llm_dependencies.py

# Or install manually
pip install openai>=1.0.0 google-generativeai>=0.3.0 requests>=2.25.0 dashscope>=1.10.0
```

### 2. Start the system
```bash
# Start backend service
python backend/main.py

# Start frontend service
cd frontend && npm run dev
```

### 3. Configure API key
1. Visit the system settings page2. Choose an AI model provider3. Enter the corresponding API key4. Select model5. test connection6. Save configuration
## 📋 Detailed configuration instructions
### Alibaba Tongyi Qianwen (DashScope)
**Get API key:**1. Visit [Alibaba Cloud Console](https://dashscope.console.aliyun.com/)2. Open Tongyi Qianwen service3. Create API key
**Supported models:**- `qwen-plus`: Tongyi Qianwen Plus (recommended)- `qwen-max`: Tongyi Qianwen Max (the strongest performance)- `qwen-turbo`: Tongyi Qianwen Turbo (quick response)
### OpenAI

**Get API key:**1. Visit [OpenAI Platform](https://platform.openai.com/)2. Register an account and recharge3. Create API key
**Supported models:**- `gpt-3.5-turbo`: GPT-3.5 Turbo (high cost performance)- `gpt-4`: GPT-4 (high quality)- `gpt-4-turbo`: GPT-4 Turbo (latest and most powerful)
### Google Gemini

**Get API key:**1. Visit [Google AI Studio](https://ai.google.dev/)2. Log in to Google account
3. Create API key
**Supported models:**- `gemini-2.5-flash`: Gemini 2.5 Flash (fast)- `gemini-1.5-pro`: Gemini 1.5 Pro (high quality)- `gemini-1.5-flash`: Gemini 1.5 Flash (balanced)
### silicon based flow
**Get API key:**1. Visit [Silicon Flow Console](https://cloud.siliconflow.cn/)2. Register an account3. Create API key
**Supported models:**- `Qwen/Qwen2.5-7B-Instruct`: Qwen2.5-7B
- `Qwen/Qwen2.5-14B-Instruct`: Qwen2.5-14B
- `Qwen/Qwen2.5-32B-Instruct`: Qwen2.5-32B
- `deepseek-ai/DeepSeek-V2.5`: DeepSeek-V2.5

## 🔧 Technical implementation
### core components
#### 1. LLMProvider abstract base class
```python
class LLMProvider(ABC):
    @abstractmethod
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        """Call model API"""
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """Test API connection"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """Get available model list"""
        pass
```

#### 2. provider factory
```python
class LLMProviderFactory:
    _providers = {
        ProviderType.DASHSCOPE: DashScopeProvider,
        ProviderType.OPENAI: OpenAIProvider,
        ProviderType.GEMINI: GeminiProvider,
        ProviderType.SILICONFLOW: SiliconFlowProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_type: ProviderType, api_key: str, model_name: str, **kwargs) -> LLMProvider:
        """Create provider instance"""
        pass
```

#### 3. LLM Manager
```python
class LLMManager:
    def __init__(self, settings_file: Optional[Path] = None):
        """Initialize manager"""
        pass
    
    def set_provider(self, provider_type: ProviderType, api_key: str, model_name: str):
        """Set provider"""
        pass
    
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> str:
        """Call LLM"""
        pass
```

### API interface
#### Settings management
```http
GET /api/v1/settings
POST /api/v1/settings
```

#### Connection test
```http
POST /api/v1/settings/test-api-key
```

#### Model query
```http
GET /api/v1/settings/available-models
GET /api/v1/settings/current-provider
```

## 🎨 Front-end interface
### Set page functions
1. **Provider Selection**: Drop down to select the AI ​​model provider2. **API key input**: Dynamically display the key input box of the corresponding provider3. **Model Selection**: Displays available models based on selected provider4. **Connection Test**: Test whether the API key and model are available5. **Status Display**: Shows the currently used provider and model
### Interface features
- Responsive design supports different screen sizes- Dark theme, consistent with the overall style of the system- Real-time status feedback, operation results are displayed immediately- Detailed instructions and help information
## 🔍 Troubleshooting
### FAQ
#### 1. Invalid API key
**Symptoms**: Test connection failed, prompting "API Key is invalid"
**Solution**:- Check if the API key is copied correctly- Confirm that the API key is activated- Check whether the account balance is sufficient
#### 2. Network connection issues
**Symptoms**: Connection timeout or network error
**Solution**:- Check network connection- Confirm firewall settings- Try using a proxy (if needed)
#### 3. Model not available
**Symptoms**: The selected model cannot be used
**Solution**:- Check if the model name is correct- Confirm whether the account has permission to use the model- Try switching to other available models
#### 4. Dependency package issues
**Symptoms**: Import errors or functional abnormalities
**Solution**:```bash
# Reinstall dependencies
python install_llm_dependencies.py

# or install manually
pip install --upgrade openai google-generativeai requests dashscope
```

### Log view
The system records detailed logs in the following locations:
- Backend log: `logs/backend.log`- Front-end log: Browser Developer Tools Console
## 🚀 Extension development
### Add new provider
1. **Create provider class**:```python
class NewProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str, **kwargs):
        super().__init__(api_key, model_name, **kwargs)
    
    def call(self, prompt: str, input_data: Any = None, **kwargs) -> LLMResponse:
        # Implement API call logic
        pass
    
    def test_connection(self) -> bool:
        # Implement connection test logic
        pass
    
    def get_available_models(self) -> List[ModelInfo]:
        # Return available model list
        pass
```

2. **Register to factory**:```python
# Add in llm_providers.py
class LLMProviderFactory:
    _providers = {
        # ... existing provider
        ProviderType.NEW_PROVIDER: NewProvider,
    }
```

3. **Update front-end configuration**:```typescript
// Add in SettingsPage.tsx
const providerConfig = {
  // ... existing configuration
  new_provider: {
    name: 'New Provider',
    icon: <RobotOutlined />,
    color: '#ff4d4f',
    description: 'New provider description',
    apiKeyField: 'new_provider_api_key',
    placeholder: 'Enter new provider API key'
  }
}
```

## 📊 Performance comparison
| Provider | Response speed | Chinese understanding | Cost | Stability | Recommended scenarios ||--------|----------|----------|------|--------|----------|
| Ali Tongyi Qianwen | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Chinese content processing || OpenAI | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | High Quality Requirements || Google Gemini | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | Multimodal Requirements || Silicon based flow | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Cost-effectiveness first |
## 🎯 Best Practices
1. **Choose the right provider**: Choose the most appropriate provider based on specific needs2. **Test the connection regularly**: Ensure API keys and models are always available3. **Monitor Usage**: Avoid exceeding quota limits4. **Backup Configuration**: Regularly back up API keys and configuration information5. **Secure Storage**: Don't hardcode API keys in your code
## 📞Technical support
If you encounter problems during use, you can get help in the following ways:
1. View system log files2. Check API provider official documentation3. Contact the technical support team
---

**Note**: Please keep your API key safe and do not expose it in public places or unsafe environments. It is recommended to rotate API keys regularly to ensure security.
