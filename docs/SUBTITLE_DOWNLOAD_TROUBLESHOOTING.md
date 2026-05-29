# 🎬 Subtitle Download Troubleshooting Guide

## 📋 Overview

This guide helps users solve problems with failed video subtitle downloads on Bilibili and YouTube. Failed subtitle downloads are one of the most common issues reported by users, mainly involving:

1. **Bilibili subtitles require login**
2. **YouTube subtitle format incompatibility**
3. **Speech recognition backup configuration issues**
4. **Network connection and permission issues**

## 🔍 Problem Diagnosis

### Use Diagnostic Tools

We provide specialized diagnostic tools to help troubleshoot issues:

```bash
# Check speech recognition setup
python scripts/debug_subtitle_download.py --check-speech

# Diagnose Bilibili subtitle download
python scripts/debug_subtitle_download.py https://www.bilibili.com/video/BV1xx411c7mu chrome

# Diagnose YouTube subtitle download
python scripts/debug_subtitle_download.py https://www.youtube.com/watch?v=dQw4w9WgXcQ chrome
```

### Common Error Messages

#### Bilibili-Related Errors

1. **"Subtitles are only available when logged in"**
   - **Reason**: Bilibili subtitles (especially AI subtitles) require login to download
   - **Solution**:
     - Log in to your Bilibili account in the browser
     - Select the corresponding browser (Chrome, Firefox, Safari, etc.)
     - Ensure you have an active Bilibili login session in the browser

2. **"Subtitle file not found"**
   - **Cause**: The video may have no subtitles or subtitle download failed
   - **Solution**:
     - Check whether the video has subtitles (on the Bilibili page)
     - Try different subtitle languages
     - Generate subtitles using speech recognition

#### YouTube-Related Errors

1. **"No subtitles available"**
   - **Cause**: The video has no subtitles or only auto-generated subtitles
   - **Solution**:
     - Check if the video has a subtitle track
     - Try downloading auto-generated subtitles
     - Generate subtitles using speech recognition

2. **"VTT format not supported"**
   - **Reason**: YouTube downloads subtitles in VTT format; conversion to SRT is required
   - **Solution**: The system converts automatically; if it fails, check file permissions

#### Speech Recognition-Related Errors

1. **"whisper: command not found"**
   - **Cause**: Whisper speech recognition tool is not installed
   - **Solution**:
     ```bash
     pip install openai-whisper
     ```

2. **"ffmpeg: command not found"**
   - **Cause**: ffmpeg is not installed
   - **Solution**:
     ```bash
     # macOS
     brew install ffmpeg
     
     # Ubuntu/Debian
     sudo apt update && sudo apt install ffmpeg
     
     # Windows
     # Download ffmpeg and add it to the PATH environment variable
     ```

3. **"Speech recognition timeout"**
   - **Cause**: Video is too long or system performance is insufficient
   - **Solution**:
     - Use smaller Whisper models (tiny, base)
     - Increase timeout
     - Check system memory and CPU usage

## 🛠️ Solutions

### 1. Bilibili Subtitle Download Optimization

#### Login Configuration

```python
# Ensure you are logged in to Bilibili in the browser
# Select the correct browser
browser = "chrome"  # or "firefox", "safari"
```

#### Multiple Subtitle Strategies

The system automatically tries the following strategies:
1. **AI subtitles priority**: Try to download AI-generated Chinese subtitles
2. **Multi-language strategy**: Try Chinese, English, and other languages
3. **No-cookies policy**: Try downloading public subtitles without cookies

#### Manual Configuration

```python
# Specify subtitle languages when downloading
ydl_opts = {
    'subtitleslangs': ['ai-zh', 'zh-Hans', 'zh', 'en'],
    'writeautomaticsub': True,
    'cookiesfrombrowser': ('chrome',)
}
```

### 2. YouTube Subtitle Download Optimization

#### Subtitle Format Support

```python
# Support multiple subtitle formats
formats = ['srt', 'vtt', 'json3']
languages = ['en', 'zh-Hans', 'zh', 'ja', 'ko']
```

#### Automatic Format Conversion

The system automatically converts VTT format to SRT format:

```python
# VTT to SRT conversion
async def _convert_vtt_to_srt(vtt_path: str, srt_path: str):
    # Automatically convert time format and subtitle structure
```

### 3. Speech Recognition Alternatives

#### Install Whisper

```bash
# Install Whisper
pip install openai-whisper

# Verify installation
whisper --help
```

#### Model Selection

```python
# Choose model based on needs
models = {
    "tiny": "39MB, fastest, lower accuracy",
    "base": "74MB, faster, medium accuracy (recommended)",
    "small": "244MB, medium speed, higher accuracy",
    "medium": "769MB, slower, very high accuracy",
    "large": "1550MB, slowest, highest accuracy"
}
```

#### Language Configuration

```python
# Specify language to improve accuracy
languages = {
    "zh": "Chinese",
    "en": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "auto": "Auto-detect"
}
```

## 📊 Performance Optimization Suggestions

### 1. Network Optimization
- Use a stable internet connection
- Avoid downloading during peak hours
- Consider using a proxy or VPN

### 2. System Optimization
- Ensure sufficient disk space
- Close unnecessary applications
- Use SSD storage to improve I/O performance

### 3. Configuration Optimization

```python
# Optimize download configuration
ydl_opts = {
    'format': 'best[ext=mp4]/best',  # Select best quality
    'writesubtitles': True,
    'writeautomaticsub': True,
    'subtitleslangs': ['ai-zh', 'zh-Hans', 'en'],
    'subtitlesformat': 'srt',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': False,  # Show warning messages
}
```

## 🔧 Advanced Troubleshooting

### 1. Check yt-dlp Version

```bash
# Update to latest version
pip install --upgrade yt-dlp

# Check version
yt-dlp --version
```

### 2. Check Browser Cookies

```bash
# Ensure the browser has valid cookies
# Visit Bilibili/YouTube in the browser and log in
# Verify cookies are valid
```

### 3. Test Network Connection

```bash
# Test network connection
ping www.bilibili.com
ping www.youtube.com

# Test DNS resolution
nslookup www.bilibili.com
nslookup www.youtube.com
```

### 4. Check File Permissions

```bash
# Check download directory permissions
ls -la /path/to/download/directory

# Ensure write permission
chmod 755 /path/to/download/directory
```

## 📞 Get Help

### 1. View Logs

```bash
# View detailed logs
tail -f backend.log

# View error logs
grep "ERROR" backend.log
```

### 2. Use Diagnostic Tools

```bash
# Full diagnosis
python scripts/debug_subtitle_download.py <url> <browser>

# Check speech recognition
python scripts/debug_subtitle_download.py --check-speech
```

### 3. FAQ

**Q: Why do Bilibili subtitle downloads always fail?**

A: Bilibili subtitles often require login to download. Log in to your Bilibili account in the browser and select the correct browser.

**Q: What should I do if YouTube subtitle download fails?**

A: Try the following:
1. Check if the video has subtitles
2. Try different subtitle languages
3. Generate subtitles using speech recognition

**Q: What should I do if speech recognition is very slow?**

A:
1. Use a smaller model (tiny or base)
2. Increase timeout
3. Check system performance

**Q: How to improve subtitle download success rate?**

A: Suggestions:
1. Ensure stable network connection
2. Use the latest version of yt-dlp
3. Configure browser cookies correctly
4. Install Whisper as a backup

## 🎯 Best Practices

### 1. Daily Use Suggestions
- Prefer Bilibili/YouTube native subtitles
- Configure speech recognition as a backup
- Regularly update yt-dlp and Whisper
- Keep your browser logged in

### 2. Batch Processing Suggestions
- Process large numbers of videos in batches
- Monitor system resource usage
- Set reasonable timeouts
- Save diagnostic results for analysis

### 3. Error Handling Suggestions
- Log detailed error information
- Use diagnostic tools to analyze problems
- Try multiple solutions
- Provide timely feedback to the development team

---

With the above guide, you should be able to resolve most subtitle download issues. If the problem persists, use the diagnostic tool to generate a detailed report and contact the technical support team.
