# 🎤 bcut-asr integration instructions
## 📋 Overview
AutoClip has now successfully integrated the bcut-asr speech recognition interface, implementing the strategy of calling the bcut-asr interface first and automatically falling back to the whisper local model in case of failure. This greatly improves the speed of speech recognition while maintaining system reliability.
## ✨ Main features
### 🚀 Performance advantages- **Faster**: bcut-asr is a cloud service, and the recognition speed is much faster than local whisper- **High Accuracy**: Must-Cut's speech recognition technology has a high accuracy rate- **Supports multiple formats**: Supports `flac`, `aac`, `m4a`, `mp3`, `wav` and other audio formats- **Automatic transcoding**: Automatically call ffmpeg to process video audio and other formats
### 🔄 Intelligent rollback mechanism- **Main method**: Prioritize using bcut-asr for speech recognition- **Fallback method**: When bcut-asr fails, automatically switch to the whisper local model- **Seamless switching**: Users do not need manual intervention, the system handles it automatically
### 🎯 Multiple output formats- **SRT**: Standard subtitle format (default)- **JSON**: Structured data format- **LRC**: lyrics format- **TXT**: plain text format
## 🔧 Installation and configuration
### 🚀 Automatic installation (recommended)
The system will automatically handle the installation of bcut-asr, no manual operation is required:
```python
# Use directly; the system will install dependencies automatically
from backend.utils.speech_recognizer import generate_subtitle_for_video
from pathlib import Path

video_path = Path("your_video.mp4")
subtitle_path = generate_subtitle_for_video(video_path, method="auto")
```

### 📋 Manual installation (alternative)
If the automatic installation fails, you can install it manually:
#### 1. Run the automated installation script
```bash
# Run the automatic installation script
python scripts/install_bcut_asr.py

# Or run the environment setup script
python scripts/setup_speech_recognition.py
```

#### 2. Install bcut-asr manually
```bash
# Clone the repository
git clone https://github.com/SocialSisterYi/bcut-asr.git
cd bcut-asr

# Install dependencies
poetry lock
poetry build -f wheel

# Install the package
pip install dist/bcut_asr-0.0.3-py3-none-any.whl
```

#### 3. Make sure ffmpeg is installed
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```

#### 4. Get installation instructions
```bash
# Run the manual installation guide script
python scripts/manual_install_guide.py
```

### 3. Verify installation
```bash
# Run the test script
python scripts/test_auto_install.py
```

## 🚀 How to use
### Auto mode (recommended)
```python
from backend.utils.speech_recognizer import generate_subtitle_for_video
from pathlib import Path

# Automatically select the best method (bcut-asr first, fallback to whisper on failure)
video_path = Path("your_video.mp4")
subtitle_path = generate_subtitle_for_video(
    video_path, 
    method="auto", 
    enable_fallback=True
)
```

### Manually specify method
```python
from backend.utils.speech_recognizer import (
    SpeechRecognizer, 
    SpeechRecognitionConfig, 
    SpeechRecognitionMethod
)

# Create configuration
config = SpeechRecognitionConfig(
    method=SpeechRecognitionMethod.BCUT_ASR,
    fallback_method=SpeechRecognitionMethod.WHISPER_LOCAL,
    enable_fallback=True,
    output_format="srt"
)

# Create recognizer
recognizer = SpeechRecognizer(config)

# Generate subtitles
subtitle_path = recognizer.generate_subtitle(video_path, config=config)
```

### Only use bcut-asr
```python
config = SpeechRecognitionConfig(
    method=SpeechRecognitionMethod.BCUT_ASR,
    enable_fallback=False  # Disable fallback
)
```

### Only use whisper
```python
config = SpeechRecognitionConfig(
    method=SpeechRecognitionMethod.WHISPER_LOCAL,
    enable_fallback=False
)
```

## 📊 Method priority
The system automatically selects the speech recognition method according to the following priorities:
1. **bcut-asr** - Cloud service, fast2. **whisper_local** - local model, high reliability3. **openai_api** - OpenAI API (configuration required)4. **azure_speech** - Azure Speech Service (configuration required)5. **google_speech** - Google Voice service (requires configuration)6. **aliyun_speech** - Alibaba Cloud Voice Service (configuration required)
## 🔍 Status check
### Check available methods
```python
from backend.utils.speech_recognizer import get_available_speech_recognition_methods

available_methods = get_available_speech_recognition_methods()
print(available_methods)
# Output: {'bcut_asr': True, 'whisper_local': True, ...}
```

### Check recognizer status
```python
from backend.utils.speech_recognizer import SpeechRecognizer

recognizer = SpeechRecognizer()
available_methods = recognizer.get_available_methods()
supported_languages = recognizer.get_supported_languages()
whisper_models = recognizer.get_whisper_models()
```

## ⚠️ Notes
### Network requirements- bcut-asr requires network connection- If the network is unstable, the system will automatically fall back to whisper
### File size limit- bcut-asr may have limitations on file size- For very large files, it is recommended to compress or segment them first.
### privacy considerations- bcut-asr will upload the audio to the cloud- It is recommended to use local whisper for sensitive content
## 🐛 Troubleshooting
### bcut-asr is not available```bash
# Check if it is installed
python -c "import bcut_asr; print('bcut-asr is installed')"

# Reinstall
pip uninstall bcut-asr
# Then follow the installation steps to reinstall
```

### ffmpeg is not available```bash
# Check ffmpeg
ffmpeg -version

# If not installed, follow the installation steps above
```

### Fallback mechanism not working```python
# Check available methods
available_methods = get_available_speech_recognition_methods()
print(f"bcut-asr: {available_methods.get('bcut_asr', False)}")
print(f"whisper: {available_methods.get('whisper_local', False)}")
```

## 📈 Performance comparison
| Methodology | Speed ​​| Accuracy | Network Requirements | Privacy ||------|------|--------|----------|--------|
| bcut-asr | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Required | Cloud processing || whisper | ⭐⭐ | ⭐⭐⭐⭐⭐ | Not required | Local processing |
## 🔮 Future plans
1. **More cloud services**: Integrate more speech recognition services2. **Smart selection**: Intelligent selection method based on file size and network conditions3. **Batch Processing**: Supports speech recognition of batch files4. **Real-time recognition**: Support real-time speech recognition
## 📞Technical support
If you encounter problems, please:
1. View the log file `logs/backend.log`2. Run the test script `python scripts/test_bcut_asr_integration.py`3. Check network connection and dependency installation4. Submit Issue to project repository
---

**🎉 Now you can enjoy a faster speech recognition experience! **
