"""
Speech recognition utility - Supports multiple speech recognition services
Supports local Whisper, OpenAI API, Azure Speech Services, and other speech recognition services
"""
import logging
import subprocess
import json
import os
import asyncio
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from enum import Enum
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import bcut-asr
try:
    from bcut_asr import BcutASR
    from bcut_asr.orm import ResultStateEnum
    BCUT_ASR_AVAILABLE = True
except ImportError:
    BCUT_ASR_AVAILABLE = False
    logger.warning("bcut-asr is not installed, will skip bcut-asr method")

def _auto_install_bcut_asr():
    """Automatically install bcut-asr"""
    try:
        import subprocess
        import sys
        from pathlib import Path
        
        # Get the installation script path
        script_path = Path(__file__).parent.parent.parent / "scripts" / "install_bcut_asr.py"
        
        if not script_path.exists():
            logger.error("Installation script does not exist, please install bcut-asr manually")
            _show_manual_install_guide()
            return False
        
        logger.info("Starting automatic installation of bcut-asr...")
        
        # Run the installation script
        result = subprocess.run([
            sys.executable, str(script_path)
        ], capture_output=True, text=True, timeout=600)  # 10-minute timeout
        
        if result.returncode == 0:
            logger.info("bcut-asr automatic installation succeeded")
            return True
        else:
            logger.error(f"bcut-asr automatic installation failed: {result.stderr}")
            _show_manual_install_guide()
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("bcut-asr installation timed out")
        _show_manual_install_guide()
        return False
    except Exception as e:
        logger.error(f"bcut-asr automatic installation failed: {e}")
        _show_manual_install_guide()
        return False

def _show_manual_install_guide():
    """Show manual installation guide"""
    logger.info("Manual installation guide:")
    logger.info("1. Install ffmpeg:")
    logger.info("   macOS: brew install ffmpeg")
    logger.info("   Ubuntu: sudo apt install ffmpeg")
    logger.info("   Windows: winget install ffmpeg")
    logger.info("2. Install bcut-asr:")
    logger.info("   git clone https://github.com/SocialSisterYi/bcut-asr.git")
    logger.info("   cd bcut-asr && pip install .")
    logger.info("3. Run manual installation script:")
    logger.info("   python scripts/manual_install_guide.py")

def _ensure_bcut_asr_available():
    """Ensure bcut-asr is available, attempt automatic installation if not"""
    global BCUT_ASR_AVAILABLE
    
    if BCUT_ASR_AVAILABLE:
        return True
    
    logger.info("bcut-asr is not available, attempting automatic installation...")
    
    if _auto_install_bcut_asr():
        # Try importing again
        try:
            from bcut_asr import BcutASR
            from bcut_asr.orm import ResultStateEnum
            BCUT_ASR_AVAILABLE = True
            logger.info("bcut-asr installation succeeded, it is now available")
            return True
        except ImportError:
            logger.error("bcut-asr still cannot be imported after installation")
            return False
    else:
        logger.warning("bcut-asr automatic installation failed, will use other methods")
        return False


class SpeechRecognitionMethod(str, Enum):
    """Speech recognition method enumeration"""
    BCUT_ASR = "bcut_asr"
    WHISPER_LOCAL = "whisper_local"
    OPENAI_API = "openai_api"
    AZURE_SPEECH = "azure_speech"
    GOOGLE_SPEECH = "google_speech"
    ALIYUN_SPEECH = "aliyun_speech"


class LanguageCode(str, Enum):
    """Supported language codes"""
    # Chinese
    CHINESE_SIMPLIFIED = "zh"
    CHINESE_TRADITIONAL = "zh-TW"
    # English
    ENGLISH = "en"
    ENGLISH_US = "en-US"
    ENGLISH_UK = "en-GB"
    # Japanese
    JAPANESE = "ja"
    # Korean
    KOREAN = "ko"
    # French
    FRENCH = "fr"
    # German
    GERMAN = "de"
    # Spanish
    SPANISH = "es"
    # Russian
    RUSSIAN = "ru"
    # Arabic
    ARABIC = "ar"
    # Portuguese
    PORTUGUESE = "pt"
    # Italian
    ITALIAN = "it"
    # Auto detect
    AUTO = "auto"


@dataclass
class SpeechRecognitionConfig:
    """Speech recognition configuration"""
    method: SpeechRecognitionMethod = SpeechRecognitionMethod.BCUT_ASR
    language: LanguageCode = LanguageCode.AUTO
    model: str = "base"  # Whisper model size
    timeout: int = 0  # Timeout in seconds, 0 means unlimited
    output_format: str = "srt"  # Output format
    enable_timestamps: bool = True  # Whether to enable timestamps
    enable_punctuation: bool = True  # Whether to enable punctuation
    enable_speaker_diarization: bool = False  # Whether to enable speaker diarization
    enable_fallback: bool = True  # Whether to enable fallback mechanism
    fallback_method: SpeechRecognitionMethod = SpeechRecognitionMethod.WHISPER_LOCAL  # Fallback method
    
    def __post_init__(self):
        """Validate configuration parameters"""
        # Validate method
        if not isinstance(self.method, SpeechRecognitionMethod):
            try:
                self.method = SpeechRecognitionMethod(self.method)
            except ValueError:
                raise ValueError(f"Unsupported speech recognition method: {self.method}")
        
        # Validate language
        if not isinstance(self.language, LanguageCode):
            try:
                self.language = LanguageCode(self.language)
            except ValueError:
                raise ValueError(f"Unsupported language code: {self.language}")
        
        # Validate model
        valid_models = ["tiny", "base", "small", "medium", "large"]
        if self.model not in valid_models:
            raise ValueError(f"Unsupported Whisper model: {self.model}")
        
        # Validate timeout
        if self.timeout < 0:
            raise ValueError("Timeout cannot be negative")
        
        # Validate output format
        valid_formats = ["srt", "vtt", "txt", "json"]
        if self.output_format not in valid_formats:
            raise ValueError(f"Unsupported output format: {self.output_format}")


class SpeechRecognitionError(Exception):
    """Speech recognition error"""
    pass


class SpeechRecognizer:
    """Speech recognizer supporting multiple speech recognition services"""
    
    def __init__(self, config: Optional[SpeechRecognitionConfig] = None):
        self.config = config or SpeechRecognitionConfig()
        self.available_methods = self._check_available_methods()
    
    def _check_available_methods(self) -> Dict[SpeechRecognitionMethod, bool]:
        """Check available speech recognition methods"""
        methods = {}
        
        # Check bcut-asr
        methods[SpeechRecognitionMethod.BCUT_ASR] = self._check_bcut_asr_availability()
        
        # Check local Whisper
        methods[SpeechRecognitionMethod.WHISPER_LOCAL] = self._check_whisper_availability()
        
        # Check OpenAI API
        methods[SpeechRecognitionMethod.OPENAI_API] = self._check_openai_availability()
        
        # Check Azure Speech Services
        methods[SpeechRecognitionMethod.AZURE_SPEECH] = self._check_azure_speech_availability()
        
        # Check Google Speech-to-Text
        methods[SpeechRecognitionMethod.GOOGLE_SPEECH] = self._check_google_speech_availability()
        
        # Check Alibaba Cloud speech recognition
        methods[SpeechRecognitionMethod.ALIYUN_SPEECH] = self._check_aliyun_speech_availability()
        
        return methods
    
    def _check_bcut_asr_availability(self) -> bool:
        """Check if bcut-asr is available, attempt automatic installation if not"""
        if BCUT_ASR_AVAILABLE:
            return True
        
        # Try automatic installation
        logger.info("bcut-asr is not available, attempting automatic installation...")
        if _ensure_bcut_asr_available():
            return True
        
        logger.warning("bcut-asr is not available and automatic installation failed")
        return False
    
    def _check_whisper_availability(self) -> bool:
        """Check if local Whisper is available"""
        try:
            result = subprocess.run(['whisper', '--help'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Local Whisper is not installed or unavailable")
            return False
    
    def _check_openai_availability(self) -> bool:
        """Check if OpenAI API is available"""
        api_key = os.getenv("OPENAI_API_KEY")
        return api_key is not None and len(api_key.strip()) > 0
    
    def _check_azure_speech_availability(self) -> bool:
        """Check if Azure Speech Services is available"""
        api_key = os.getenv("AZURE_SPEECH_KEY")
        region = os.getenv("AZURE_SPEECH_REGION")
        return api_key is not None and region is not None
    
    def _check_google_speech_availability(self) -> bool:
        """Check if Google Speech-to-Text is available"""
        # Check Google Cloud credentials file
        cred_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if cred_file and Path(cred_file).exists():
            return True
        
        # Check API key
        api_key = os.getenv("GOOGLE_SPEECH_API_KEY")
        return api_key is not None
    
    def _check_aliyun_speech_availability(self) -> bool:
        """Check if Alibaba Cloud speech recognition is available"""
        access_key = os.getenv("ALIYUN_ACCESS_KEY_ID")
        secret_key = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
        app_key = os.getenv("ALIYUN_SPEECH_APP_KEY")
        return access_key is not None and secret_key is not None and app_key is not None
    
    def _extract_audio_from_video(self, video_path: Path, output_dir: Path) -> Path:
        """
        Extract audio from video file
        
        Args:
            video_path: Video file path
            output_dir: Output directory
            
        Returns:
            Extracted audio file path
        """
        try:
            # Check if ffmpeg is available
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise SpeechRecognitionError("ffmpeg is not available, please install ffmpeg")
            
            # Generate audio file path
            audio_filename = f"{video_path.stem}_audio.wav"
            audio_path = output_dir / audio_filename
            
            # If audio file already exists, return directly
            if audio_path.exists():
                logger.info(f"Audio file already exists: {audio_path}")
                return audio_path
            
            logger.info(f"Extracting audio from video: {video_path} -> {audio_path}")
            
            # Use ffmpeg to extract audio
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-vn',  # Do not process video stream
                '-acodec', 'pcm_s16le',  # Use PCM 16-bit encoding
                '-ar', '16000',  # Sample rate 16kHz
                '-ac', '1',  # Mono channel
                '-y',  # Overwrite output file
                str(audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                raise SpeechRecognitionError(f"Audio extraction failed: {result.stderr}")
            
            if not audio_path.exists():
                raise SpeechRecognitionError("Audio extraction failed, output file does not exist")
            
            logger.info(f"Audio extraction succeeded: {audio_path}")
            return audio_path
            
        except subprocess.TimeoutExpired:
            raise SpeechRecognitionError("Audio extraction timed out")
        except Exception as e:
            raise SpeechRecognitionError(f"Audio extraction failed: {e}")
    
    def generate_subtitle(self, video_path: Path, output_path: Optional[Path] = None, 
                         config: Optional[SpeechRecognitionConfig] = None) -> Path:
        """
        Generate subtitle file
        
        Args:
            video_path: Video file path
            output_path: Output subtitle file path
            config: Speech recognition configuration
            
        Returns:
            Generated subtitle file path
            
        Raises:
            SpeechRecognitionError: Speech recognition failed
        """
        if not video_path.exists():
            raise SpeechRecognitionError(f"Video file does not exist: {video_path}")
        
        # Use passed config or default config
        config = config or self.config
        
        # Determine output path
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}.{config.output_format}"
        
        # Select recognition service based on configured method, support fallback mechanism
        try:
            if config.method == SpeechRecognitionMethod.BCUT_ASR:
                return self._generate_subtitle_bcut_asr(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.WHISPER_LOCAL:
                return self._generate_subtitle_whisper_local(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.OPENAI_API:
                return self._generate_subtitle_openai_api(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.AZURE_SPEECH:
                return self._generate_subtitle_azure_speech(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.GOOGLE_SPEECH:
                return self._generate_subtitle_google_speech(video_path, output_path, config)
            elif config.method == SpeechRecognitionMethod.ALIYUN_SPEECH:
                return self._generate_subtitle_aliyun_speech(video_path, output_path, config)
            else:
                raise SpeechRecognitionError(f"Unsupported speech recognition method: {config.method}")
        except SpeechRecognitionError as e:
            # If fallback is enabled and current method is not the fallback method, try fallback
            if (config.enable_fallback and 
                config.method != config.fallback_method and 
                self.available_methods.get(config.fallback_method, False)):
                
                logger.warning(f"Primary method {config.method} failed: {e}")
                logger.info(f"Attempting fallback to {config.fallback_method}")
                
                # Create fallback config
                fallback_config = SpeechRecognitionConfig(
                    method=config.fallback_method,
                    language=config.language,
                    model=config.model,
                    timeout=config.timeout,
                    output_format=config.output_format,
                    enable_timestamps=config.enable_timestamps,
                    enable_punctuation=config.enable_punctuation,
                    enable_speaker_diarization=config.enable_speaker_diarization,
                    enable_fallback=False  # Avoid infinite fallback
                )
                
                return self.generate_subtitle(video_path, output_path, fallback_config)
            else:
                raise
    
    def _generate_subtitle_bcut_asr(self, video_path: Path, output_path: Path, 
                                   config: SpeechRecognitionConfig) -> Path:
        """Generate subtitles using bcut-asr"""
        # Ensure bcut-asr is available
        if not _ensure_bcut_asr_available():
            raise SpeechRecognitionError(
                "bcut-asr is not available and automatic installation failed, please install manually:\n"
                "1. Run: python scripts/install_bcut_asr.py\n"
                "2. Or install manually: git clone https://github.com/SocialSisterYi/bcut-asr.git\n"
                "3. Also ensure ffmpeg is installed:\n"
                "   macOS: brew install ffmpeg\n"
                "   Ubuntu: sudo apt install ffmpeg\n"
                "   Windows: winget install ffmpeg"
            )
        
        try:
            logger.info(f"Starting subtitle generation with bcut-asr: {video_path}")
            
            # Check if video file exists
            if not video_path.exists():
                raise SpeechRecognitionError(f"Video file does not exist: {video_path}")
            
            # Check video file size
            file_size = video_path.stat().st_size
            if file_size == 0:
                raise SpeechRecognitionError(f"Video file is empty: {video_path}")
            
            # Check file format, extract audio first if it's a video file
            audio_path = self._extract_audio_from_video(video_path, output_path.parent)
            
            # Create BcutASR instance, use audio file
            asr = BcutASR(str(audio_path))
            
            # Upload file
            logger.info("Uploading file to bcut-asr...")
            asr.upload()
            
            # Create task
            logger.info("Creating recognition task...")
            asr.create_task()
            
            # Poll for results
            logger.info("Waiting for recognition results...")
            max_attempts = 60  # Wait up to 5 minutes (check every 5 seconds)
            attempt = 0
            
            while attempt < max_attempts:
                result = asr.result()
                
                # Check if recognition succeeded
                if result.state == ResultStateEnum.COMPLETE:
                    logger.info("bcut-asr recognition completed")
                    break
                elif result.state == ResultStateEnum.FAILED:
                    raise SpeechRecognitionError("bcut-asr recognition failed")
                
                # Wait 5 seconds before retrying
                import time
                time.sleep(5)
                attempt += 1
                logger.info(f"Waiting for recognition results... ({attempt}/{max_attempts})")
            else:
                raise SpeechRecognitionError("bcut-asr recognition timed out")
            
            # Parse subtitle content
            subtitle = result.parse()
            
            # Check if subtitles exist
            if not subtitle.has_data():
                raise SpeechRecognitionError("bcut-asr did not recognize any valid subtitle content")
            
            # Save subtitles based on output format
            if config.output_format == "srt":
                subtitle_content = subtitle.to_srt()
            elif config.output_format == "json":
                subtitle_content = subtitle.to_json()
            elif config.output_format == "lrc":
                subtitle_content = subtitle.to_lrc()
            elif config.output_format == "txt":
                subtitle_content = subtitle.to_txt()
            else:
                # Default to srt format
                subtitle_content = subtitle.to_srt()
            
            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(subtitle_content)
            
            logger.info(f"bcut-asr subtitle generation succeeded: {output_path}")
            return output_path
            
        except Exception as e:
            error_msg = f"Error occurred during bcut-asr subtitle generation: {e}\n"
            error_msg += "Possible reasons:\n"
            error_msg += "1. Network connection issues\n"
            error_msg += "2. Unsupported file format\n"
            error_msg += "3. File is too large\n"
            error_msg += "4. bcut-asr service temporarily unavailable"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_whisper_local(self, video_path: Path, output_path: Path, 
                                       config: SpeechRecognitionConfig) -> Path:
        """Generate subtitles using local Whisper"""
        if not self.available_methods[SpeechRecognitionMethod.WHISPER_LOCAL]:
            raise SpeechRecognitionError(
                "Local Whisper is not available, please install whisper: pip install openai-whisper\n"
                "Also ensure ffmpeg is installed:\n"
                "  macOS: brew install ffmpeg\n"
                "  Ubuntu: sudo apt install ffmpeg\n"
                "  Windows: Download ffmpeg and add to PATH"
            )
        
        try:
            logger.info(f"Starting subtitle generation with local Whisper: {video_path}")
            
            # Check if video file exists
            if not video_path.exists():
                raise SpeechRecognitionError(f"Video file does not exist: {video_path}")
            
            # Check video file size
            file_size = video_path.stat().st_size
            if file_size == 0:
                raise SpeechRecognitionError(f"Video file is empty: {video_path}")
            
            # Build whisper command
            cmd = [
                'whisper',
                str(video_path),
                '--output_dir', str(output_path.parent),
                '--output_format', config.output_format,
                '--model', config.model
            ]
            
            # Add language parameter
            if config.language != LanguageCode.AUTO:
                cmd.extend(['--language', config.language])
            
            # Add timeout handling
            logger.info(f"Executing Whisper command: {' '.join(cmd)}")
            
            # Decide whether to set timeout based on config
            if config.timeout > 0:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=config.timeout,
                    cwd=str(video_path.parent)  # Set working directory
                )
            else:
                # No timeout limit
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    cwd=str(video_path.parent)  # Set working directory
                )
            
            if result.returncode == 0:
                # Check if output file exists
                if output_path.exists():
                    logger.info(f"Local Whisper subtitle generation succeeded: {output_path}")
                    return output_path
                else:
                    # Try to find other possible output files
                    possible_outputs = list(output_path.parent.glob(f"{video_path.stem}*.{config.output_format}"))
                    if possible_outputs:
                        actual_output = possible_outputs[0]
                        logger.info(f"Found Whisper output file: {actual_output}")
                        return actual_output
                    else:
                        raise SpeechRecognitionError(f"Whisper executed successfully but output file not found: {output_path}")
            else:
                error_msg = f"Local Whisper execution failed (return code: {result.returncode}):\n"
                if result.stderr:
                    error_msg += f"Error message: {result.stderr}\n"
                if result.stdout:
                    error_msg += f"Output message: {result.stdout}"
                
                # Provide specific error resolution suggestions
                if "command not found" in result.stderr:
                    error_msg += "\n\nSolution: Please install whisper: pip install openai-whisper"
                elif "ffmpeg" in result.stderr.lower():
                    error_msg += "\n\nSolution: Please install ffmpeg:\n  macOS: brew install ffmpeg\n  Ubuntu: sudo apt install ffmpeg"
                elif "timeout" in result.stderr.lower():
                    error_msg += f"\n\nSolution: Video processing timed out, try using a smaller model (--model tiny) or increase timeout"
                
                logger.error(error_msg)
                raise SpeechRecognitionError(error_msg)
                
        except subprocess.TimeoutExpired:
            error_msg = f"Local Whisper execution timed out ({config.timeout} seconds)\n"
            error_msg += "Solutions:\n"
            error_msg += "1. Use a smaller model: --model tiny\n"
            error_msg += "2. Increase timeout\n"
            error_msg += "3. Check if video file is corrupted"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
        except FileNotFoundError:
            error_msg = "whisper command not found\n"
            error_msg += "Solutions:\n"
            error_msg += "1. Install whisper: pip install openai-whisper\n"
            error_msg += "2. Ensure whisper is in PATH: which whisper\n"
            error_msg += "3. Reinstall: pip uninstall openai-whisper && pip install openai-whisper"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
        except Exception as e:
            error_msg = f"Error occurred during local Whisper subtitle generation: {e}\n"
            error_msg += "Please check:\n"
            error_msg += "1. Whether video file format is supported\n"
            error_msg += "2. Whether system has enough memory\n"
            error_msg += "3. Whether there is enough disk space"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_openai_api(self, video_path: Path, output_path: Path, 
                                    config: SpeechRecognitionConfig) -> Path:
        """Generate subtitles using OpenAI API"""
        if not self.available_methods[SpeechRecognitionMethod.OPENAI_API]:
            raise SpeechRecognitionError("OpenAI API is not available, please set the OPENAI_API_KEY environment variable")
        
        try:
            logger.info(f"Starting subtitle generation with OpenAI API: {video_path}")
            
            # OpenAI API call needs to be implemented here
            # Due to additional dependencies required, throw exception for now
            raise SpeechRecognitionError("OpenAI API feature is not yet implemented, please use local Whisper")
            
        except Exception as e:
            error_msg = f"Error occurred during OpenAI API subtitle generation: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_azure_speech(self, video_path: Path, output_path: Path, 
                                      config: SpeechRecognitionConfig) -> Path:
        """Generate subtitles using Azure Speech Services"""
        if not self.available_methods[SpeechRecognitionMethod.AZURE_SPEECH]:
            raise SpeechRecognitionError("Azure Speech Services is not available, please set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION environment variables")
        
        try:
            logger.info(f"Starting subtitle generation with Azure Speech Services: {video_path}")
            
            # Azure Speech Services call needs to be implemented here
            raise SpeechRecognitionError("Azure Speech Services feature is not yet implemented, please use local Whisper")
            
        except Exception as e:
            error_msg = f"Error occurred during Azure Speech Services subtitle generation: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_google_speech(self, video_path: Path, output_path: Path, 
                                       config: SpeechRecognitionConfig) -> Path:
        """Generate subtitles using Google Speech-to-Text"""
        if not self.available_methods[SpeechRecognitionMethod.GOOGLE_SPEECH]:
            raise SpeechRecognitionError("Google Speech-to-Text is not available, please set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SPEECH_API_KEY environment variable")
        
        try:
            logger.info(f"Starting subtitle generation with Google Speech-to-Text: {video_path}")
            
            # Google Speech-to-Text call needs to be implemented here
            raise SpeechRecognitionError("Google Speech-to-Text feature is not yet implemented, please use local Whisper")
            
        except Exception as e:
            error_msg = f"Error occurred during Google Speech-to-Text subtitle generation: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def _generate_subtitle_aliyun_speech(self, video_path: Path, output_path: Path, 
                                       config: SpeechRecognitionConfig) -> Path:
        """Generate subtitles using Alibaba Cloud speech recognition"""
        if not self.available_methods[SpeechRecognitionMethod.ALIYUN_SPEECH]:
            raise SpeechRecognitionError("Alibaba Cloud speech recognition is not available, please set ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, and ALIYUN_SPEECH_APP_KEY environment variables")
        
        try:
            logger.info(f"Starting subtitle generation with Alibaba Cloud speech recognition: {video_path}")
            
            # Alibaba Cloud speech recognition call needs to be implemented here
            raise SpeechRecognitionError("Alibaba Cloud speech recognition feature is not yet implemented, please use local Whisper")
            
        except Exception as e:
            error_msg = f"Error occurred during Alibaba Cloud speech recognition subtitle generation: {e}"
            logger.error(error_msg)
            raise SpeechRecognitionError(error_msg)
    
    def get_available_methods(self) -> Dict[SpeechRecognitionMethod, bool]:
        """Get available speech recognition methods"""
        return self.available_methods.copy()
    
    def get_supported_languages(self) -> List[LanguageCode]:
        """Get list of supported languages"""
        return list(LanguageCode)
    
    def get_whisper_models(self) -> List[str]:
        """Get list of available Whisper models"""
        return ["tiny", "base", "small", "medium", "large"]


def generate_subtitle_for_video(video_path: Path, output_path: Optional[Path] = None, 
                               method: str = "auto", language: str = "auto", 
                               model: str = "base", enable_fallback: bool = True) -> Path:
    """
    Convenience function for generating subtitle files for videos
    
    Args:
        video_path: Video file path
        output_path: Output subtitle file path
        method: Generation method ("auto", "bcut_asr", "whisper_local", "openai_api", "azure_speech", "google_speech", "aliyun_speech")
        language: Language code
        model: Whisper model size (only effective for whisper_local)
        enable_fallback: Whether to enable fallback mechanism
        
    Returns:
        Generated subtitle file path
        
    Raises:
        SpeechRecognitionError: Speech recognition failed
    """
    # Create config
    config = SpeechRecognitionConfig(
        method=SpeechRecognitionMethod(method) if method != "auto" else SpeechRecognitionMethod.BCUT_ASR,
        language=LanguageCode(language),
        model=model,
        enable_fallback=enable_fallback
    )
    
    recognizer = SpeechRecognizer()
    
    if method == "auto":
        # Automatically select the best method
        available_methods = recognizer.get_available_methods()
        
        # Select method by priority (bcut-asr first, as it's faster)
        priority_methods = [
            SpeechRecognitionMethod.BCUT_ASR,
            SpeechRecognitionMethod.WHISPER_LOCAL,
            SpeechRecognitionMethod.OPENAI_API,
            SpeechRecognitionMethod.AZURE_SPEECH,
            SpeechRecognitionMethod.GOOGLE_SPEECH,
            SpeechRecognitionMethod.ALIYUN_SPEECH
        ]
        
        for priority_method in priority_methods:
            if available_methods.get(priority_method, False):
                config.method = priority_method
                break
        else:
            raise SpeechRecognitionError("No available speech recognition service, please install whisper or configure API key")
    
    return recognizer.generate_subtitle(video_path, output_path, config)


def get_available_speech_recognition_methods() -> Dict[str, bool]:
    """
    Get available speech recognition methods
    
    Returns:
        Dictionary of available methods
    """
    recognizer = SpeechRecognizer()
    available_methods = recognizer.get_available_methods()
    
    return {
        method.value: available 
        for method, available in available_methods.items()
    }


def get_supported_languages() -> List[str]:
    """
    Get list of supported languages
    
    Returns:
        List of supported language codes
    """
    return [lang.value for lang in LanguageCode]


def get_whisper_models() -> List[str]:
    """
    Get list of available Whisper models
    
    Returns:
        List of Whisper models
    """
    return ["tiny", "base", "small", "medium", "large"]
