# 🎤 Voice Recognition Setup Guide
## 📋 Overview
AutoClip supports multiple speech recognition methods to generate subtitle files. When the video does not have subtitles, the system will automatically generate subtitles to ensure that the pipeline processing can proceed normally.
## 🔧Supported voice recognition methods
### 1. Local Whisper (recommended)
**Features:**- ✅ Runs completely locally, no internet required- ✅ No API key required- ✅ Free to use- ✅Support multiple languages- ✅High accuracy
**Installation method:**
```bash
# Method 1: Install with pip
pip install openai-whisper

# Method 2: Install with conda
conda install -c conda-forge openai-whisper

# Method 3: Install from source
git clone https://github.com/openai/whisper.git
cd whisper
pip install -e .
```

**Verify installation:**```bash
whisper --help
```

**Model selection:**- `tiny`: 39MB, fastest, low accuracy- `base`: 74MB, fast, medium accuracy (default)- `small`: 244MB, medium speed, high accuracy- `medium`: 769MB, slower, very accurate- `large`: 1550MB, the slowest and the highest accuracy
### 2. OpenAI API (planned)
**Features:**- ✅ Highest accuracy- ✅Support multiple languages- ❌ Requires API key- ❌ Internet connection required- ❌ There is a usage fee
**Setting method:**```bash
# Set environment variables
export OPENAI_API_KEY="your-api-key-here"
```

### 3. Test subtitles (alternative)
**Features:**- ✅ No need to install any dependencies- ✅ Available immediately- ❌ This is just test content, not real subtitles- ❌ The effect of pipeline processing is limited
## 🚀 How to use
### Auto mode (default)
The system automatically selects the best available method:
```python
from shared.utils.speech_recognizer import generate_subtitle_for_video

# Automatically select the best method
result = generate_subtitle_for_video(video_path, method="auto")
```

### Manually specify method
```python
# Force local Whisper
result = generate_subtitle_for_video(video_path, method="whisper_local")

# Force OpenAI API
result = generate_subtitle_for_video(video_path, method="openai_api")

# Force test subtitles
result = generate_subtitle_for_video(video_path, method="simple")
```

### Check available methods
```python
from shared.utils.speech_recognizer import get_available_speech_recognition_methods

methods = get_available_speech_recognition_methods()
print(methods)
# Example output:
# {
#     "whisper_local": True,
#     "openai_api": False,
#     "simple": True
# }
```

## 📝 Configuration options
### Modify Whisper parameters
Whisper parameters can be modified in `shared/utils/speech_recognizer.py`:
```python
cmd = [
    'whisper',
    str(video_path),
    '--output_dir', str(output_path.parent),
    '--output_format', 'srt',
    '--language', 'zh',  # Language: zh (Chinese), en (English), auto (auto-detect)
    '--model', 'base'    # Model: tiny, base, small, medium, large
]
```

### Description of common parameters
- `--language`: Specify language to improve recognition accuracy- `--model`: Select model size, affecting speed and accuracy- `--output_format`: output format, supports srt, vtt, txt, etc.- `--task`: task type, transcribe or translate
## 🔍 Troubleshooting
### Whisper installation issues
**Question:** `whisper: command not found`
**Solution:**```bash
# Check if the installation is successful
pip list | grep whisper

# Reinstall
pip uninstall openai-whisper
pip install openai-whisper

# Check PATH
which whisper
```

**Problem:** Missing dependencies
**Solution:**```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt update
sudo apt install ffmpeg

# Install system dependencies (macOS)
brew install ffmpeg

# Install Python dependencies
pip install torch torchvision torchaudio
```

### Performance optimization
**Problem:** Whisper runs too slowly
**Solution:**1. Use a smaller model: `--model tiny`2. Use GPU acceleration if available3. Process long videos in segments
**Problem:** Out of memory
**Solution:**1. Use smaller models2. Increase system memory3. Use CPU mode
## 📊 Performance comparison
| Method | Speed ​​| Accuracy | Cost | Network Dependencies | Installation Difficulty ||------|------|--------|------|----------|----------|
| Whisper tiny | ⭐⭐⭐⭐⭐ | ⭐⭐ | Free | None | Simple || Whisper base | ⭐⭐⭐⭐ | ⭐⭐⭐ | Free | None | Simple || Whisper small | ⭐⭐⭐ | ⭐⭐⭐⭐ | Free | None | Simple || Whisper medium | ⭐⭐ | ⭐⭐⭐⭐⭐ | Free | None | Simple || OpenAI API | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Paid | Required | Simple || Test subtitles | ⭐⭐⭐⭐⭐ | ⭐ | Free | None | No installation required |
## 🎯 Recommended configuration
### development environment```bash
# Install base model (balance speed and accuracy)
pip install openai-whisper
```

### production environment```bash
# Install small or medium model (higher accuracy)
pip install openai-whisper
# Consider using GPU acceleration
```

### test environment```bash
# No installation required, use test subtitles
# The system will automatically generate a test subtitle file
```

## 📞Technical support
If you encounter problems, please:
1. Check the log file for error messages2. Verify Whisper is installed correctly3. Confirm whether the video file format is supported4. Check whether system resources are sufficient
For more help please refer to:- [Whisper official documentation](https://github.com/openai/whisper)- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
