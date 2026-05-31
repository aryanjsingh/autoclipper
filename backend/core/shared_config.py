"""
Configuration File - Manage API keys, file paths, and other configuration
Supports new configuration management system and backward compatibility
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pydantic import BaseModel, validator
from enum import Enum

from .kiro_gateway import (
    DEFAULT_MODEL as DEFAULT_KIRO_MODEL,
    get_gateway_api_key,
    get_gateway_base_url,
)
from .output_language import OUTPUT_LANGUAGE, is_english, speech_recognition_language

# Video category enumeration
class VideoCategory(str, Enum):
    DEFAULT = "default"
    KNOWLEDGE = "knowledge"
    BUSINESS = "business"
    OPINION = "opinion"
    EXPERIENCE = "experience"
    SPEECH = "speech"
    CONTENT_REVIEW = "content_review"
    ENTERTAINMENT = "entertainment"

# Video category configuration (English when AUTOCLIP_OUTPUT_LANGUAGE=en)
VIDEO_CATEGORIES_CONFIG = {
    VideoCategory.DEFAULT: {
        "name": "General",
        "description": "General video content for most use cases",
        "icon": "🎬",
        "color": "#4facfe"
    },
    VideoCategory.KNOWLEDGE: {
        "name": "Knowledge",
        "description": "Education, science, and technical explainers",
        "icon": "📚",
        "color": "#52c41a"
    },
    VideoCategory.BUSINESS: {
        "name": "Business",
        "description": "Business analysis, finance, and investing",
        "icon": "💼",
        "color": "#faad14"
    },
    VideoCategory.OPINION: {
        "name": "Opinion",
        "description": "Opinion pieces, commentary, and debate",
        "icon": "💭",
        "color": "#722ed1"
    },
    VideoCategory.EXPERIENCE: {
        "name": "Experience",
        "description": "Life lessons, skills, and practical tips",
        "icon": "🌟",
        "color": "#13c2c2"
    },
    VideoCategory.SPEECH: {
        "name": "Speech & Talk",
        "description": "Talks, podcasts, stand-up, and interviews",
        "icon": "🎤",
        "color": "#eb2f96"
    },
    VideoCategory.CONTENT_REVIEW: {
        "name": "Reviews",
        "description": "Film, game, and media commentary",
        "icon": "🎭",
        "color": "#f5222d"
    },
    VideoCategory.ENTERTAINMENT: {
        "name": "Entertainment",
        "description": "Shows, variety, and light entertainment",
        "icon": "🎪",
        "color": "#fa8c16"
    }
}

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Input file paths
INPUT_DIR = PROJECT_ROOT / "input"
INPUT_VIDEO = INPUT_DIR / "input.mp4"
INPUT_SRT = INPUT_DIR / "input.srt"
INPUT_TXT = INPUT_DIR / "input.txt"

# Output directories
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"
CLIPS_DIR = OUTPUT_DIR / "clips"
COLLECTIONS_DIR = OUTPUT_DIR / "collections"
METADATA_DIR = OUTPUT_DIR / "metadata"

# Prompt file paths
PROMPT_DIR = Path(__file__).parent.parent / "prompt"
PROMPT_FILES = {
    "outline": PROMPT_DIR / "outline.txt",
    "timeline": PROMPT_DIR / "timestamps.txt",
    "recommendation": PROMPT_DIR / "recommendation.txt",
    "title": PROMPT_DIR / "title_generation.txt",
    "clustering": PROMPT_DIR / "topic_clustering.txt",
    "collection_title": PROMPT_DIR / "collection_title.txt",
    "caption": PROMPT_DIR / "caption.txt"
}

# API configuration
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
MODEL_NAME = os.getenv("API_MODEL_NAME") or os.getenv("KIRO_GATEWAY_MODEL") or DEFAULT_KIRO_MODEL

# Speech recognition configuration
SPEECH_RECOGNITION_METHOD = os.getenv("SPEECH_RECOGNITION_METHOD", "whisper_local")
SPEECH_RECOGNITION_LANGUAGE = speech_recognition_language()
SPEECH_RECOGNITION_MODEL = os.getenv("SPEECH_RECOGNITION_MODEL", "base")
SPEECH_RECOGNITION_TIMEOUT = int(os.getenv("SPEECH_RECOGNITION_TIMEOUT", "1000"))

# Processing parameters
CHUNK_SIZE = 5000  # Text chunk size
MIN_SCORE_THRESHOLD = 0.75  # Minimum engagement score (0-1) a clip must reach to be kept. 0.75 = the "yes, publish" band in recommendation.txt; gates to only the few clips worth posting.
TOP_FALLBACK_CLIP_COUNT = 3  # If none pass MIN_SCORE_THRESHOLD, keep this many highest-scored clips anyway
MAX_CLIPS_PER_COLLECTION = 5  # (Legacy) collections/compilations are disabled for the X clipper

# Clip duration bounds for the X (Twitter) podcast clipper.
# Every published clip must fall inside [MIN_CLIP_SECONDS, MAX_CLIP_SECONDS].
MIN_CLIP_SECONDS = 30    # Hard minimum: 30 seconds
MAX_CLIP_SECONDS = 120   # Hard maximum: 2 minutes (tightened from 180 — clips were drifting long)
TARGET_CLIP_SECONDS = 60  # Sweet spot for a punchy, hook-first standalone clip (~45-75s)

# Corner watermark on final clips (X logo + @handle), applied in step 6.
WATERMARK_ENABLED = os.getenv("AUTOCLIP_WATERMARK_ENABLED", "true").lower() in ("1", "true", "yes")
WATERMARK_USERNAME = os.getenv("AUTOCLIP_WATERMARK_USERNAME", "ARYNNSGH")

# Topic extraction control parameters
MIN_TOPIC_DURATION_MINUTES = 2  # Minimum topic duration (minutes)
MAX_TOPIC_DURATION_MINUTES = 12  # Maximum topic duration (minutes)
TARGET_TOPIC_DURATION_MINUTES = 5  # Target topic duration (minutes)
MIN_TOPICS_PER_CHUNK = 3  # Minimum topics per text chunk
MAX_TOPICS_PER_CHUNK = 8  # Maximum topics per text chunk

# Ensure output directories exist
for dir_path in [CLIPS_DIR, COLLECTIONS_DIR, METADATA_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# New configuration management system
class Settings(BaseModel):
    """System settings"""
    llm_provider: str = "kiro"
    dashscope_api_key: Optional[str] = ""
    kiro_api_key: Optional[str] = ""
    kiro_base_url: Optional[str] = ""
    model_name: str = DEFAULT_KIRO_MODEL
    chunk_size: int = 5000
    min_score_threshold: float = 0.7
    max_clips_per_collection: int = 5
    max_retries: int = 3
    timeout_seconds: int = 30
    # Topic extraction control parameters
    min_topic_duration_minutes: int = 2
    max_topic_duration_minutes: int = 12
    target_topic_duration_minutes: int = 5
    min_topics_per_chunk: int = 3
    max_topics_per_chunk: int = 8
    # Speech recognition configuration
    speech_recognition_method: str = "whisper_local"
    speech_recognition_language: str = "auto"
    speech_recognition_model: str = "base"
    speech_recognition_timeout: int = 1000
    # Bilibili upload configuration (bilitool-related features removed)
    # bilibili_auto_upload: bool = False
    # bilibili_default_tid: int = 21  # Default partition: daily
    # bilibili_max_concurrent_uploads: int = 3
    # bilibili_upload_timeout_minutes: int = 30
    # bilibili_auto_generate_tags: bool = True
    # bilibili_tag_limit: int = 12
    
    @validator('min_score_threshold')
    def validate_score_threshold(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Score threshold must be between 0 and 1')
        return v
    
    @validator('chunk_size')
    def validate_chunk_size(cls, v):
        if v <= 0:
            raise ValueError('Chunk size must be greater than 0')
        return v

@dataclass
class APIConfig:
    """API configuration"""
    provider: str = "kiro"
    model_name: str = DEFAULT_KIRO_MODEL
    api_key: Optional[str] = None
    base_url: str = "https://dashscope.aliyuncs.com"
    max_tokens: int = 4096

@dataclass
class ProcessingConfig:
    """Processing configuration"""
    chunk_size: int = 5000
    min_score_threshold: float = 0.7
    max_clips_per_collection: int = 5
    max_retries: int = 3
    timeout_seconds: int = 30

# @dataclass
# class BilibiliConfig:
#     """Bilibili upload configuration (bilitool-related features removed)"""
#     auto_upload: bool = False
#     default_tid: int = 21  # Default partition: daily
#     max_concurrent_uploads: int = 3
#     upload_timeout_minutes: int = 30
#     auto_generate_tags: bool = True
#     tag_limit: int = 12

@dataclass
class PathConfig:
    """Path configuration"""
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)
    data_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "data")
    uploads_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "uploads")
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "output")
    prompt_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "prompt")
    temp_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "temp")

class ConfigManager:
    """Configuration manager"""
    
    def __init__(self):
        self.settings = Settings()
        self._load_settings()
        self._setup_prompt_files()
    
    def _load_settings(self):
        """Load settings"""
        # Load from environment variables
        if os.getenv("DASHSCOPE_API_KEY"):
            self.settings.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        
        # Load from configuration file
        config_file = PROJECT_ROOT / "data" / "settings.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    for key, value in config_data.items():
                        if hasattr(self.settings, key):
                            setattr(self.settings, key, value)
            except Exception as e:
                print(f"Failed to load configuration file: {e}")
    
    def _setup_prompt_files(self):
        """Set up prompt files"""
        self.prompt_files = PROMPT_FILES.copy()
        
        # Ensure prompt directory exists
        PROMPT_DIR.mkdir(exist_ok=True)
        
        # Create default prompt files
        default_prompts = {
            "outline.txt": "Please analyze the following video content and extract main topics and structure:\n\n{content}",
            "timestamps.txt": "Please locate specific time intervals for the following topics:\n\n{content}",
            "recommendation.txt": "Please evaluate the quality and recommendability of the following content:\n\n{content}",
            "title_generation.txt": "Please generate an attractive title for the following content:\n\n{content}",
            "topic_clustering.txt": "Please cluster the following topics by theme:\n\n{content}"
        }
        
        for filename, content in default_prompts.items():
            file_path = PROMPT_DIR / filename
            if not file_path.exists():
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                except Exception as e:
                    print(f"Failed to create prompt file {filename}: {e}")
    
    def get_api_config(self) -> APIConfig:
        """Get API configuration"""
        if self.settings.llm_provider == "kiro":
            return APIConfig(
                provider="kiro",
                model_name=self.settings.model_name,
                api_key=get_gateway_api_key(self.settings.kiro_api_key),
                base_url=get_gateway_base_url(self.settings.kiro_base_url)
            )

        return APIConfig(
            provider=self.settings.llm_provider,
            model_name=self.settings.model_name,
            api_key=self.settings.dashscope_api_key
        )
    
    def get_processing_config(self) -> ProcessingConfig:
        """Get processing configuration"""
        return ProcessingConfig(
            chunk_size=self.settings.chunk_size,
            min_score_threshold=self.settings.min_score_threshold,
            max_clips_per_collection=self.settings.max_clips_per_collection,
            max_retries=self.settings.max_retries,
            timeout_seconds=self.settings.timeout_seconds
        )
    
    def get_path_config(self) -> PathConfig:
        """Get path configuration"""
        return PathConfig()
    
    # def get_bilibili_config(self) -> BilibiliConfig:
    #     """Get Bilibili upload configuration (bilitool-related features removed)"""
    #     return BilibiliConfig(
    #         auto_upload=self.settings.bilibili_auto_upload,
    #         default_tid=self.settings.bilibili_default_tid,
    #         max_concurrent_uploads=self.settings.bilibili_max_concurrent_uploads,
    #         upload_timeout_minutes=self.settings.bilibili_upload_timeout_minutes,
    #         auto_generate_tags=self.settings.bilibili_auto_generate_tags,
    #         tag_limit=self.settings.bilibili_tag_limit
    #     )
    
    def ensure_project_directories(self, project_id: str):
        """Ensure project directory structure exists"""
        paths = self.get_project_paths(project_id)
        
        for path in paths.values():
            if isinstance(path, Path):
                path.mkdir(parents=True, exist_ok=True)
    
    def get_project_paths(self, project_id: str) -> Dict[str, Path]:
        """Get project path configuration"""
        data_dir = self.get_path_config().data_dir
        projects_dir = data_dir / "projects"
        project_base = projects_dir / project_id
        
        return {
            "project_base": project_base,
            "input_dir": project_base / "raw",  # Changed to raw directory
            "output_dir": project_base / "output",
            "clips_dir": project_base / "output" / "clips",
            "collections_dir": project_base / "output" / "collections",
            "metadata_dir": project_base / "output" / "metadata",
            "logs_dir": project_base / "logs",
            "temp_dir": project_base / "temp"
        }
    
    def update_api_key(self, api_key: str):
        """Update API key"""
        self.settings.dashscope_api_key = api_key
        os.environ["DASHSCOPE_API_KEY"] = api_key
        
        # Save to configuration file
        self._save_settings()
    
    def update_settings(self, **kwargs):
        """Update settings"""
        for key, value in kwargs.items():
            if hasattr(self.settings, key):
                setattr(self.settings, key, value)
        
        self._save_settings()
    
    def _save_settings(self):
        """Save settings to file"""
        config_file = PROJECT_ROOT / "data" / "settings.json"
        config_file.parent.mkdir(exist_ok=True)
        
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings.dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Failed to save configuration file: {e}")
    
    def export_config(self) -> Dict[str, Any]:
        """Export configuration"""
        return {
            "api_config": {
                "model_name": self.settings.model_name,
                "api_key": self.settings.dashscope_api_key[:8] + "..." if self.settings.dashscope_api_key else None
            },
            "processing_config": {
                "chunk_size": self.settings.chunk_size,
                "min_score_threshold": self.settings.min_score_threshold,
                "max_clips_per_collection": self.settings.max_clips_per_collection,
                "max_retries": self.settings.max_retries,
                "timeout_seconds": self.settings.timeout_seconds
            },
            # "bilibili_config": {
            #     "auto_upload": self.settings.bilibili_auto_upload,
            #     "default_tid": self.settings.bilibili_default_tid,
            #     "max_concurrent_uploads": self.settings.bilibili_max_concurrent_uploads,
            #     "upload_timeout_minutes": self.settings.bilibili_upload_timeout_minutes,
            #     "auto_generate_tags": self.settings.bilibili_auto_generate_tags,
            #     "tag_limit": self.settings.bilibili_tag_limit
            # },  # bilitool-related features removed
            "paths": {
                "project_root": str(self.get_path_config().project_root),
                "data_dir": str(self.get_path_config().data_dir),
                "uploads_dir": str(self.get_path_config().uploads_dir),
                "output_dir": str(self.get_path_config().output_dir),
                "prompt_dir": str(self.get_path_config().prompt_dir)
            }
        }

PROMPT_KEY_FILENAMES_ZH = {
    "outline": "outline.txt",
    "timeline": "timestamps.txt",
    "recommendation": "recommendation.txt",
    "title": "title_generation.txt",
    "clustering": "topic_clustering.txt",
    "collection_title": "collection_title.txt",
    "caption": "caption.txt",
}

PROMPT_KEY_FILENAMES_EN = {
    "outline": "outline.txt",
    "timeline": "timeline.txt",
    "recommendation": "recommendation.txt",
    "title": "title.txt",
    "clustering": "clustering.txt",
    "collection_title": "collection_title.txt",
    "caption": "caption.txt",
}


def _first_existing_path(candidates: list[Path]) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def get_prompt_files(video_category: str = VideoCategory.DEFAULT) -> Dict[str, Path]:
    """
    Resolve prompt files for a video/project category and output language.
    English prompts live under backend/prompt/languages/en/ (and category subdirs).
    """
    category = (
        video_category.value
        if hasattr(video_category, "value")
        else str(video_category or VideoCategory.DEFAULT)
    )
    use_english = is_english()
    filenames = PROMPT_KEY_FILENAMES_EN if use_english else PROMPT_KEY_FILENAMES_ZH
    lang_dir = PROMPT_DIR / "languages" / OUTPUT_LANGUAGE if use_english else None

    resolved: Dict[str, Path] = {}
    for key, filename in filenames.items():
        candidates: list[Path] = []
        if lang_dir is not None:
            candidates.append(lang_dir / category / filename)
            candidates.append(lang_dir / filename)
        if category and category != VideoCategory.DEFAULT:
            candidates.append(PROMPT_DIR / category / PROMPT_KEY_FILENAMES_ZH[key])
        candidates.append(PROMPT_DIR / PROMPT_KEY_FILENAMES_ZH[key])

        match = _first_existing_path(candidates)
        if match is not None:
            resolved[key] = match
        else:
            resolved[key] = PROMPT_DIR / PROMPT_KEY_FILENAMES_ZH[key]

    return resolved

# Create global configuration manager instance
config_manager = ConfigManager()

def get_legacy_config() -> Dict[str, Any]:
    """Get backward-compatible configuration"""
    return {
        'PROJECT_ROOT': PROJECT_ROOT,
        'INPUT_DIR': INPUT_DIR,
        'INPUT_VIDEO': INPUT_VIDEO,
        'INPUT_SRT': INPUT_SRT,
        'INPUT_TXT': INPUT_TXT,
        'OUTPUT_DIR': OUTPUT_DIR,
        'CLIPS_DIR': CLIPS_DIR,
        'COLLECTIONS_DIR': COLLECTIONS_DIR,
        'METADATA_DIR': METADATA_DIR,
        'PROMPT_DIR': PROMPT_DIR,
        'PROMPT_FILES': PROMPT_FILES,
        'DASHSCOPE_API_KEY': DASHSCOPE_API_KEY,
        'MODEL_NAME': MODEL_NAME,
        'CHUNK_SIZE': CHUNK_SIZE,
        'MIN_SCORE_THRESHOLD': MIN_SCORE_THRESHOLD,
        'MAX_CLIPS_PER_COLLECTION': MAX_CLIPS_PER_COLLECTION,
        'MIN_TOPIC_DURATION_MINUTES': MIN_TOPIC_DURATION_MINUTES,
        'MAX_TOPIC_DURATION_MINUTES': MAX_TOPIC_DURATION_MINUTES,
        'TARGET_TOPIC_DURATION_MINUTES': TARGET_TOPIC_DURATION_MINUTES,
        'MIN_TOPICS_PER_CHUNK': MIN_TOPICS_PER_CHUNK,
        'MAX_TOPICS_PER_CHUNK': MAX_TOPICS_PER_CHUNK
    }
