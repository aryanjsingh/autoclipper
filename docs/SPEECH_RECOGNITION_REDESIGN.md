# 🎤 Redesigned speech recognition module
## 📋 Overview
Based on user needs, we have completely redesigned the speech recognition module. The main improvements include:
1. **Remove test subtitle data** - If the transcription fails, the task failure will be reported directly, and the mock data will no longer be used.2. **Supports multi-language recognition** - supports Chinese, English, Japanese, Korean and other languages3. **Supports multiple API access** - Supports local Whisper, OpenAI API, Azure Speech Services, etc.
## 🔧 Major improvements
### 1. Remove test subtitles feature
**Previous question:**- When speech recognition fails, the system generates a test subtitle file- The content of test subtitles is inaccurate, which affects the quality of subsequent processing.- Users may mistakenly believe that processing is successful
**Now improvements:**- Completely remove test subtitle generation functionality- Throw an exception directly when speech recognition fails- Ensure data quality in production environments
```python
# Before: return None or test subtitles
result = generate_subtitle_for_video(video_path)
if result is None:
    # Generate test subtitles...

# Now: throw exception on failure
try:
    result = generate_subtitle_for_video(video_path)
except SpeechRecognitionError as e:
    # Handle speech recognition failure
    logger.error(f"Speech recognition failed: {e}")
    raise
```

### 2. Multilingual support
**Supported languages:**- Chinese (Simplified/Traditional)- English (American/British)- Japanese- Korean- French- German- spanish- Russian- Arabic- portuguese- Italian- Automatic detection
**How to use:**```python
from shared.utils.speech_recognizer import generate_subtitle_for_video, LanguageCode

# Specify language
result = generate_subtitle_for_video(
    video_path, 
    language=LanguageCode.CHINESE_SIMPLIFIED
)

# Automatically detect language
result = generate_subtitle_for_video(
    video_path, 
    language=LanguageCode.AUTO
)
```

### 3. Various speech recognition services
**Supported Services:**
| Services | Features | Configuration Requirements ||------|------|----------|
| Local Whisper | Free, offline, high accuracy | Install whisper and ffmpeg || OpenAI API | Highest accuracy, supports multiple languages ​​| OpenAI API key || Azure Speech | Enterprise-grade, feature-rich | Azure account and API key || Google Speech | High accuracy and advanced features | Google Cloud account || Alibaba Cloud Voice | Good Chinese recognition effect | Alibaba Cloud account and API key |
**Automatic selection strategy:**1. Local Whisper (recommended)2. OpenAI API
3. Azure Speech Services
4. Google Speech-to-Text
5. Alibaba Cloud Speech Recognition
## 🚀 New API interface
### Speech recognition status query
```bash
GET /api/v1/speech-recognition/status
```

return:```json
{
  "available_methods": {
    "whisper_local": true,
    "openai_api": false,
    "azure_speech": false,
    "google_speech": false,
    "aliyun_speech": false
  },
  "supported_languages": ["zh", "en", "ja", "ko", "auto"],
  "whisper_models": ["tiny", "base", "small", "medium", "large"],
  "default_config": {
    "method": "whisper_local",
    "language": "auto",
    "model": "base",
    "timeout": 300
  }
}
```

### Configuration test
```bash
POST /api/v1/speech-recognition/test
```

Request body:```json
{
  "method": "whisper_local",
  "language": "zh",
  "model": "base",
  "timeout": 300
}
```

### Installation guide
```bash
GET /api/v1/speech-recognition/install-guide?method=whisper_local
```

## 📝 Configuration management
### Environment variable configuration
```bash
# speech recognition method
export SPEECH_RECOGNITION_METHOD="whisper_local"

# Language settings
export SPEECH_RECOGNITION_LANGUAGE="zh"

# Whisper model
export SPEECH_RECOGNITION_MODEL="base"

# timeout
export SPEECH_RECOGNITION_TIMEOUT="300"

# API key (based on selected service)
export OPENAI_API_KEY="your-openai-key"
export AZURE_SPEECH_KEY="your-azure-key"
export AZURE_SPEECH_REGION="your-region"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
export ALIYUN_ACCESS_KEY_ID="your-access-key"
export ALIYUN_ACCESS_KEY_SECRET="your-secret-key"
export ALIYUN_SPEECH_APP_KEY="your-app-key"
```

### Configuration file
Configurable in `data/settings.json`:
```json
{
  "speech_recognition_method": "whisper_local",
  "speech_recognition_language": "zh",
  "speech_recognition_model": "base",
  "speech_recognition_timeout": 300
}
```

## 🔍 Error handling
### New exception type
```python
from shared.utils.speech_recognizer import SpeechRecognitionError

try:
    result = generate_subtitle_for_video(video_path)
except SpeechRecognitionError as e:
    # Handling speech recognition errors
    logger.error(f"Speech recognition failed: {e}")
    # You can choose to try again or use another method
```

### error type
1. **Service Unavailable** - The specified speech recognition service is not installed or configured2. **File does not exist** - The video file does not exist or is inaccessible3. **Execution Timeout** - Speech recognition processing timeout4. **Execution Failure** - Speech recognition service execution failed5. **Configuration Error** - Parameter configuration is incorrect
## 📊Performance optimization
### Whisper model selection
| Model | Size | Speed ​​| Accuracy | Applicable scenarios ||------|------|------|--------|----------|
| tiny | 39MB | ⭐⭐⭐⭐⭐ | ⭐⭐ | Quick Test || base | 74MB | ⭐⭐⭐⭐ | ⭐⭐⭐ | Daily use || small | 244MB | ⭐⭐⭐ | ⭐⭐⭐⭐ | High quality requirements || medium | 769MB | ⭐⭐ | ⭐⭐⭐⭐⭐ | Professional use || large | 1550MB | ⭐ | ⭐⭐⭐⭐⭐ | Highest Quality |
### Timeout settings
- Short video (<5 minutes): 60 seconds- Medium video (5-30 minutes): 300 seconds- Long video (>30 minutes): 600 seconds
## 🛠️Installation Guide
### Local Whisper installation
```bash
# Install Python dependencies
pip install openai-whisper

# Install system dependencies
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download ffmpeg and add to PATH

# Verify installation
whisper --help
```

### API service configuration
#### OpenAI API
```bash
export OPENAI_API_KEY="your-api-key"
```

#### Azure Speech Services
```bash
export AZURE_SPEECH_KEY="your-api-key"
export AZURE_SPEECH_REGION="your-region"
```

#### Google Speech-to-Text
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
```

#### Alibaba Cloud Speech Recognition```bash
export ALIYUN_ACCESS_KEY_ID="your-access-key"
export ALIYUN_ACCESS_KEY_SECRET="your-secret-key"
export ALIYUN_SPEECH_APP_KEY="your-app-key"
```

## 🔄 Migration Guide
### Migrate from older versions
1. **Update import statement**```python
# old version
from shared.utils.speech_recognizer import generate_subtitle_for_video

# new version
from shared.utils.speech_recognizer import (
    generate_subtitle_for_video, 
    SpeechRecognitionError,
    LanguageCode
)
```

2. **Updated error handling**```python
# Old version
result = generate_subtitle_for_video(video_path)
if result is None:
    # Handle failure

# New version
try:
    result = generate_subtitle_for_video(video_path)
except SpeechRecognitionError as e:
    # Handle failure
```

3. **Remove test subtitle related code**```python
# delete these codes
if method == "simple":
    return recognizer.generate_subtitle_simple(video_path, output_path)
```

## 📈 Monitoring and logging
### logging
```python
import logging
logger = logging.getLogger(__name__)

# Voice recognition starts
logger.info(f"Start speech recognition: {video_path}")

# Voice recognition successful
logger.info(f"Speech recognition successful: {output_path}")

# Voice recognition failed
logger.error(f"Speech recognition failed: {error}")
```

### Performance monitoring
It is recommended to monitor the following indicators:- Voice recognition success rate- processing time- Error type distribution- Usage of different services
## 🎯 Best Practices
1. **Production Environment Recommendations**   - Use `small` or `medium` model   - Set a reasonable timeout   - Configure error retry mechanism
2. **Multi-language processing**   - Prioritize automatic language detection   - For language-specific content, explicitly specify the language code   - Consider using a dedicated speech recognition service
3. **Error handling**   - Implement elegant error handling   - Provide user-friendly error messages   - Consider a downgrade strategy
4. **Performance Optimization**   - Choose the right model based on video length   - Use GPU acceleration if available   - Consider processing multiple videos in parallel
## 🔮 Future plans
1. **Implement more API services**   - Baidu speech recognition   - Tencent Cloud Speech Recognition   - Huawei Cloud Speech Recognition
2. **Enhanced Features**   - speaker separation   - emotion recognition   - Keyword extraction
3. **Performance Optimization**   - streaming   - caching mechanism   - distributed processing
## 📞Technical support
If you encounter problems, please:
1. Check the log file for error messages2. Verify that the speech recognition service is installed correctly3. Confirm that the configuration file is correct4. View API documentation and installation guide
For more help please refer to:- [Whisper official documentation](https://github.com/openai/whisper)- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)- [Azure Speech Services Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/speech-service/)- [Google Speech-to-Text Documentation](https://cloud.google.com/speech-to-text/docs)- [Alibaba Cloud Speech Recognition Document](https://help.aliyun.com/product/30413.html)
