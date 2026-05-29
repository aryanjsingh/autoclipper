# Optional SRT file upload feature guide
## Overview
AutoClip now supports two upload methods:1. **Video + Subtitle File**: User uploads video and SRT subtitle file at the same time2. **Video files only**: Users only upload video files, and the system automatically uses speech recognition to generate subtitles.
## Features
### ✅ Smart upload mode- **User priority**: If the user provides subtitle files, the user's subtitles will be used first- **AI Assisted**: If the user only uploads videos, speech recognition is automatically called to generate subtitles.- **Error handling**: When speech recognition fails, clearly report error information to the user
### ✅Multi-language support- Supports speech recognition in 15 languages- Intelligent selection of recognition language based on video classification:  - Business/Knowledge Category: Priority is given to Chinese recognition  - Entertainment: Automatically detect language  - Others: Automatically detect language
### ✅ Multiple voice recognition methods- Local Whisper (recommended)- OpenAI API
- Azure Speech Services
- Google Speech-to-Text
- Alibaba Cloud Speech Recognition
## How to use
### Front-end interface changes
1. **Upload Tips Update**   - Original text: Subtitle files (.srt) must be imported at the same time   - New text: You can choose to import subtitle files (.srt) or use AI to automatically generate them
2. **Smart Tips**   - Upload video + subtitles: display two files   - Only upload videos: Display "Subtitle files will be automatically generated using AI speech recognition"
3. **Upload button logic**   - Original: Need video + subtitles + project name   - Now: Just need video + project name
### API interface changes
#### Upload interface `POST /api/v1/projects/upload`
**Parameter changes:**```python
# Before: srt_file was required
srt_file: UploadFile = File(...)

# Now: srt_file is optional
srt_file: Optional[UploadFile] = File(None)
```

**Request Example:**
1. **Upload video and subtitles at the same time**```python
files = {
    'video_file': ('video.mp4', video_content, 'video/mp4'),
    'srt_file': ('subtitle.srt', srt_content, 'application/x-subrip')
}
data = {
    'project_name': 'My Project',
    'video_category': 'knowledge'
}
```

2. **Only upload videos**```python
files = {
    'video_file': ('video.mp4', video_content, 'video/mp4')
}
data = {
    'project_name': 'My project',
    'video_category': 'knowledge'
}
```

**Response example:**
The successful response remains the same, but the item description reflects the handling:```json
{
    "id": "project-id",
    "name": "My Project",
    "description": "Video: video.mp4 (Will generate subtitle using speech recognition)",
    "settings": {
        "auto_generate_subtitle": true,
        "video_category": "knowledge"
    }
}
```

**Error handling:**
A 400 error is returned when speech recognition fails:```json
{
    "detail": "Speech recognition failed: No speech recognition service is available, please install whisper or configure API key. Please upload subtitle files manually or check the speech recognition service configuration."
}
```

## Technical implementation
### Backend implementation
1. **Parameter verification**   ```python
   # Video file validation (required)
   if not video_file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm')):
       raise HTTPException(status_code=400, detail="Invalid video file format")
   
   # Subtitle file validation (optional)
   if srt_file and not srt_file.filename.lower().endswith('.srt'):
       raise HTTPException(status_code=400, detail="Invalid subtitle file format")
   ```

2. **Subtitle processing logic**   ```python
   if srt_file:
       # Save user-supplied subtitles file
       srt_path = save_user_subtitle(srt_file)
   else:
       # Generate subtitles using speech recognition
       srt_path = generate_subtitle_with_speech_recognition(video_path, language, model)
   ```

3. **Language Selection Strategy**   ```python
   # Determine language based on video category
   language = "auto"  # Default: auto-detect
   if video_category in ["business", "knowledge"]:
       language = "zh"  # Chinese content
   elif video_category == "entertainment":
       language = "auto"  # Entertainment content may be multilingual
   ```

### Front-end implementation
1. **Upload logic modification**   ```typescript
   // Removing subtitle files requires verification
   if (!files.video) {
       message.error('Please select a video file')
       return
   }
   // if (!files.srt) { // Remove this check
   // message.error('Please import the subtitle file (.srt) at the same time')
   //     return
   // }
   ```

2. **UI prompt update**   ```typescript
   // Smart prompt
   {files.video && !files.srt && (
       <div>Subtitle files will be automatically generated using AI speech recognition</div>
   )}
   ```

3. **API call modification**   ```typescript
   const formData = new FormData()
   formData.append('video_file', data.video_file)
   if (data.srt_file) { // Only add if there is a subtitle file
       formData.append('srt_file', data.srt_file)
   }
   ```

## Configuration requirements
### Speech recognition service configuration
In order to use automatic speech recognition, at least one speech recognition service needs to be configured:
#### 1. Local Whisper (recommended)```bash
# Install Whisper
pip install openai-whisper

# Install FFmpeg
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

#### 2. OpenAI API
```bash
export OPENAI_API_KEY="your-api-key"
```

#### 3. Azure Speech Services
```bash
export AZURE_SPEECH_KEY="your-api-key"
export AZURE_SPEECH_REGION="your-region"
```

#### 4. Google Speech-to-Text
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
```

#### 5. Alibaba Cloud Speech Recognition```bash
export ALIYUN_ACCESS_KEY_ID="your-access-key"
export ALIYUN_ACCESS_KEY_SECRET="your-secret-key"
export ALIYUN_SPEECH_APP_KEY="your-app-key"
```

### Check configuration status
Speech recognition service status can be checked via the new API endpoint:
```bash
# Check available speech recognition methods
GET /api/v1/speech-recognition/status

# Response example
{
    "available_methods": {
        "whisper_local": true,
        "openai_api": false,
        "azure_speech": false,
        "google_speech": false,
        "aliyun_speech": false
    },
    "supported_languages": ["zh", "en", "ja", "ko", "fr", "de", ...],
    "whisper_models": ["tiny", "base", "small", "medium", "large"],
    "default_config": {
        "method": "whisper_local",
        "language": "auto",
        "model": "base",
        "timeout": 300
    }
}
```

## best practices
### 1. User experience optimization- **Clear Notice**: Clearly inform users that subtitle files are optional- **Processing Time**: Inform users that speech recognition may take a long time- **Error Recovery**: Provides an alternative to manually uploading subtitles
### 2. Performance considerations
- **Model Selection**: Use the `base` model by default to balance speed and accuracy- **Language Optimization**: Choose the appropriate recognition language according to the content type- **Timeout Setting**: Set the voice recognition timeout reasonably (default 5 minutes)
### 3. Error handling- **Service Check**: Checks speech recognition service availability on startup- **Downgrade Strategy**: Try different speech recognition services in order of priority- **User Friendly**: Provides clear error messages and solution suggestions
## troubleshooting
### FAQ
1. **"No speech recognition service available"**   - Check if Whisper is installed: `which whisper`   - Check if API key is configured   - View service status: `GET /api/v1/speech-recognition/status`
2. **"Speech recognition timeout"**   - Check video file size (<100MB recommended)   - Increase timeout settings   - Try using a faster model (tiny/base)
3. **"Subtitle file does not exist"**   - Check whether Whisper is installed correctly   - Check the backend logs for detailed errors   - Try running the Whisper command test manually
### Debugging steps
1. **Check service status**   ```bash
   curl http://localhost:8000/api/v1/speech-recognition/status
   ```

2. **View backend logs**   ```bash
   tail -f backend/backend.log
   ```

3. **Test Whisper installation**   ```bash
   whisper --help
   ffmpeg -version
   ```

## Change log
### v1.0.0
- ✅Supports optional SRT file upload- ✅ Integrate multiple speech recognition services- ✅ Smart language selection- ✅ Perfect error handling- ✅ User-friendly interface tips
---

## Related documents
- [Speech Recognition Redesign Document](./SPEECH_RECOGNITION_REDESIGN.md)- [Speech Recognition Setup Guide](./SPEECH_RECOGNITION_SETUP.md)- [Backend Architecture Document](./BACKEND_ARCHITECTURE.md)
