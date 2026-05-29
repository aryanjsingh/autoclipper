#!/usr/bin/env python3
"""
Bilibili video downloader - Based on yt-dlp for downloading Bilibili videos and subtitles
Integrated into the auto-clipping tool project
"""

import os
import re
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import yt_dlp

try:
    from .error_handler import FileIOError, ValidationError, ProcessingError
except ImportError:
    # Import for standalone execution
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    from ..utils.error_handler import FileIOError, ValidationError, ProcessingError

logger = logging.getLogger(__name__)

class BilibiliVideoInfo:
    """Bilibili video information class"""
    def __init__(self, info_dict: Dict[str, Any]):
        self.bvid = info_dict.get('id', '')
        self.title = info_dict.get('title', 'unknown_video')
        self.duration = info_dict.get('duration', 0)
        self.uploader = info_dict.get('uploader', 'unknown')
        self.description = info_dict.get('description', '')
        self.thumbnail_url = info_dict.get('thumbnail', '')
        self.view_count = info_dict.get('view_count', 0)
        self.upload_date = info_dict.get('upload_date', '')
        self.webpage_url = info_dict.get('webpage_url', '')
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            'bvid': self.bvid,
            'title': self.title,
            'duration': self.duration,
            'uploader': self.uploader,
            'description': self.description,
            'thumbnail_url': self.thumbnail_url,
            'view_count': self.view_count,
            'upload_date': self.upload_date,
            'webpage_url': self.webpage_url
        }

class BilibiliDownloader:
    """Bilibili video downloader"""
    
    def __init__(self, download_dir: Optional[Path] = None, browser: Optional[str] = None):
        """
        Initialize downloader
        
        Args:
            download_dir: Download directory, defaults to current directory
            browser: Browser type for obtaining cookies
        """
        self.download_dir = download_dir or Path.cwd()
        self.browser = browser
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_bilibili_url(self, url: str) -> bool:
        """
        Validate Bilibili video link format
        
        Args:
            url: Video link
            
        Returns:
            Whether it is a valid Bilibili link
        """
        bilibili_patterns = [
            r'https?://www\.bilibili\.com/video/[Bb][Vv][0-9A-Za-z]+',
            r'https?://bilibili\.com/video/[Bb][Vv][0-9A-Za-z]+',
            r'https?://b23\.tv/[0-9A-Za-z]+',
            r'https?://www\.bilibili\.com/video/av\d+',
            r'https?://bilibili\.com/video/av\d+'
        ]
        
        return any(re.match(pattern, url) for pattern in bilibili_patterns)
    
    async def get_video_info(self, url: str) -> BilibiliVideoInfo:
        """
        Get video information (without downloading)
        
        Args:
            url: Video link
            
        Returns:
            Video information object
        """
        if not self.validate_bilibili_url(url):
            raise ValidationError(f"Invalid Bilibili video link: {url}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        if self.browser:
            ydl_opts['cookiesfrombrowser'] = (self.browser.lower(),)
        
        try:
            loop = asyncio.get_event_loop()
            info_dict = await loop.run_in_executor(
                None, 
                self._extract_info_sync, 
                url, 
                ydl_opts
            )
            return BilibiliVideoInfo(info_dict)
        except Exception as e:
            raise ProcessingError(f"Failed to get video info: {str(e)}")
    
    def _extract_info_sync(self, url: str, ydl_opts: Dict[str, Any]) -> Dict[str, Any]:
        """Extract video info synchronously"""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    
    async def download_video_and_subtitle(
        self, 
        url: str, 
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, str]:
        """
        Download video and subtitle files
        
        Args:
            url: Video link
            progress_callback: Progress callback function, parameters are (status message, progress percentage)
            
        Returns:
            Dictionary containing video_path and subtitle_path
        """
        if not self.validate_bilibili_url(url):
            raise ValidationError(f"Invalid Bilibili video link: {url}")
        
        # Get video info
        video_info = await self.get_video_info(url)
        
        # Clean filename, remove special characters
        safe_title = self._sanitize_filename(video_info.title)
        
        # Set download options - Improved subtitle download strategy
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'writesubtitles': True,
            'writeautomaticsub': True,  # Also try downloading auto-generated subtitles
            'subtitleslangs': ['ai-zh', 'zh-Hans', 'zh', 'en'],  # Multiple subtitle languages
            'subtitlesformat': 'srt',  # Force SRT format
            'outtmpl': str(self.download_dir / f'{safe_title}.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'progress': True,
            'no_warnings': False,  # Show warnings for debugging
        }
        
        if self.browser:
            ydl_opts['cookiesfrombrowser'] = (self.browser.lower(),)
        
        # Add progress hook
        if progress_callback:
            ydl_opts['progress_hooks'] = [self._create_progress_hook(progress_callback)]
        
        try:
            if progress_callback:
                progress_callback("Starting video and subtitle download...", 0)
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._download_sync,
                url,
                ydl_opts
            )
            
            # Find downloaded files
            video_path = self._find_downloaded_video(safe_title)
            subtitle_path = self._find_downloaded_subtitle(safe_title)
            
            # If first attempt didn't find subtitle, try different subtitle strategies
            if not subtitle_path:
                logger.info("First subtitle download failed, trying alternative strategies...")
                subtitle_path = await self._try_alternative_subtitle_strategies(url, safe_title)
            
            if progress_callback:
                progress_callback("Download completed", 100)
            
            result = {
                'video_path': str(video_path) if video_path else '',
                'subtitle_path': str(subtitle_path) if subtitle_path else '',
                'video_info': video_info.to_dict()
            }
            
            logger.info(f"Download completed: {video_info.title}")
            return result
            
        except Exception as e:
            error_msg = f"Download failed: {str(e)}"
            if progress_callback:
                progress_callback(error_msg, 0)
            raise ProcessingError(error_msg)
    
    async def _try_alternative_subtitle_strategies(self, url: str, safe_title: str) -> Optional[Path]:
        """Try multiple subtitle acquisition strategies"""
        strategies = [
            self._try_download_with_different_langs,
            self._try_download_without_cookies,
            self._try_extract_from_video_metadata
        ]
        
        for strategy in strategies:
            try:
                subtitle_path = await strategy(url, safe_title)
                if subtitle_path:
                    logger.info(f"Alternative subtitle strategy succeeded: {strategy.__name__}")
                    return subtitle_path
            except Exception as e:
                logger.warning(f"Alternative subtitle strategy failed {strategy.__name__}: {e}")
                continue
        
        logger.warning("All subtitle acquisition strategies failed")
        return None
    
    async def _try_download_with_different_langs(self, url: str, safe_title: str) -> Optional[Path]:
        """Try downloading subtitles in different languages"""
        logger.info("Trying to download subtitles in different languages...")
        
        # Try different subtitle language combinations
        lang_combinations = [
            ['zh-Hans', 'zh'],  # Simplified Chinese
            ['en', 'en-US'],    # English
            ['ai-zh'],          # AI Chinese subtitle
            ['auto']            # Auto detect
        ]
        
        for langs in lang_combinations:
            try:
                ydl_opts = {
                    'skip_download': True,  # Only download subtitles, not video
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': langs,
                    'subtitlesformat': 'srt',
                    'outtmpl': str(self.download_dir / f'{safe_title}_sub.%(ext)s'),
                    'noplaylist': True,
                    'quiet': True,
                }
                
                if self.browser:
                    ydl_opts['cookiesfrombrowser'] = (self.browser.lower(),)
                
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._download_sync, url, ydl_opts)
                
                # Find subtitle file
                subtitle_path = self._find_downloaded_subtitle(safe_title + "_sub")
                if subtitle_path:
                    return subtitle_path
                    
            except Exception as e:
                logger.debug(f"Failed with language {langs}: {e}")
                continue
        
        return None
    
    async def _try_download_without_cookies(self, url: str, safe_title: str) -> Optional[Path]:
        """Try downloading subtitles without cookies (some public subtitles may not require login)"""
        logger.info("Trying to download subtitles without cookies...")
        
        try:
            ydl_opts = {
                'skip_download': True,  # Only download subtitles, not video
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': ['zh-Hans', 'zh', 'en'],
                'subtitlesformat': 'srt',
                'outtmpl': str(self.download_dir / f'{safe_title}_nocookie.%(ext)s'),
                'noplaylist': True,
                'quiet': True,
            }
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._download_sync, url, ydl_opts)
            
            subtitle_path = self._find_downloaded_subtitle(safe_title + "_nocookie")
            return subtitle_path
            
        except Exception as e:
            logger.debug(f"Download without cookies failed: {e}")
            return None
    
    async def _try_extract_from_video_metadata(self, url: str, safe_title: str) -> Optional[Path]:
        """Try extracting subtitle information from video metadata"""
        logger.info("Trying to extract subtitle information from video metadata...")
        
        try:
            # Get detailed video information
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            if self.browser:
                ydl_opts['cookiesfrombrowser'] = (self.browser.lower(),)
            
            loop = asyncio.get_event_loop()
            info_dict = await loop.run_in_executor(None, self._extract_info_sync, url, ydl_opts)
            
            # Check if subtitle information exists
            subtitles = info_dict.get('subtitles', {})
            auto_subtitles = info_dict.get('automatic_captions', {})
            
            if subtitles or auto_subtitles:
                logger.info(f"Found subtitle information: {list(subtitles.keys()) + list(auto_subtitles.keys())}")
                # Further processing of subtitle information can be done here
                return None  # Return None for now, can be extended later
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract video metadata: {e}")
            return None
    
    def _download_sync(self, url: str, ydl_opts: Dict[str, Any]):
        """Download synchronously"""
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    
    def _create_progress_hook(self, progress_callback: Callable[[str, float], None]):
        """Create progress callback hook"""
        def progress_hook(d):
            if d['status'] == 'downloading':
                if 'total_bytes' in d and d['total_bytes']:
                    progress = (d['downloaded_bytes'] / d['total_bytes']) * 100
                elif '_percent_str' in d:
                    # Extract number from percentage string
                    percent_str = d['_percent_str'].strip().rstrip('%')
                    try:
                        progress = float(percent_str)
                    except ValueError:
                        progress = 0
                else:
                    progress = 0
                
                speed = d.get('_speed_str', '')
                eta = d.get('_eta_str', '')
                status = f"Downloading... {speed} ETA: {eta}"
                progress_callback(status, progress)
            elif d['status'] == 'finished':
                progress_callback("Download completed, processing...", 95)
        
        return progress_hook
    
    def _sanitize_filename(self, filename: str) -> str:
        """Clean filename, remove unsafe characters"""
        # Remove or replace unsafe characters
        unsafe_chars = '<>:"/\\|?*'
        for char in unsafe_chars:
            filename = filename.replace(char, '_')
        
        # Limit filename length
        if len(filename) > 100:
            filename = filename[:100]
        
        return filename.strip()
    
    def _find_downloaded_video(self, title: str) -> Optional[Path]:
        """Find downloaded video file"""
        possible_extensions = ['.mp4', '.mkv', '.webm', '.flv']
        
        for ext in possible_extensions:
            video_path = self.download_dir / f"{title}{ext}"
            if video_path.exists():
                return video_path
        
        # If exact match fails, try fuzzy match
        for file_path in self.download_dir.glob(f"{title}*"):
            if file_path.suffix.lower() in possible_extensions:
                return file_path
        
        return None
    
    def _find_downloaded_subtitle(self, title: str) -> Optional[Path]:
        """Find downloaded subtitle file - Simplified version, focused on AI subtitles"""
        logger.info(f"Searching for subtitle file, title: {title}")
        
        # First check AI subtitle file
        ai_subtitle_path = self.download_dir / f"{title}.ai-zh.srt"
        if ai_subtitle_path.exists():
            # Rename to standard format
            standard_path = self.download_dir / f"{title}.srt"
            if not standard_path.exists():
                ai_subtitle_path.rename(standard_path)
                logger.info(f"Renamed AI subtitle file: {title}.ai-zh.srt -> {title}.srt")
                return standard_path
            return ai_subtitle_path
        
        # Check if already in standard format
        standard_path = self.download_dir / f"{title}.srt"
        if standard_path.exists():
            logger.info(f"Found standard subtitle file: {title}.srt")
            return standard_path
        
        # Fuzzy match subtitle files
        for file_path in self.download_dir.glob(f"{title}*.srt"):
            logger.info(f"Found subtitle file: {file_path.name}")
            return file_path
        
        logger.warning(f"Subtitle file not found, title: {title}")
        return None
    
    def _convert_vtt_to_srt(self, vtt_path: Path, srt_path: Path):
        """Convert VTT subtitle file to SRT format"""
        try:
            with open(vtt_path, 'r', encoding='utf-8') as vtt_file:
                vtt_content = vtt_file.read()
            
            # Simple VTT to SRT conversion
            lines = vtt_content.split('\n')
            srt_lines = []
            subtitle_count = 1
            
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                
                # Skip VTT header information
                if line.startswith('WEBVTT') or line.startswith('NOTE') or not line:
                    i += 1
                    continue
                
                # Find timestamp line
                if '-->' in line:
                    # Convert time format (VTT uses dots, SRT uses commas)
                    time_line = line.replace('.', ',')
                    srt_lines.append(str(subtitle_count))
                    srt_lines.append(time_line)
                    
                    # Get subtitle text
                    i += 1
                    subtitle_text = []
                    while i < len(lines) and lines[i].strip():
                        subtitle_text.append(lines[i].strip())
                        i += 1
                    
                    srt_lines.extend(subtitle_text)
                    srt_lines.append('')  # Empty line separator
                    subtitle_count += 1
                
                i += 1
            
            # Write SRT file
            with open(srt_path, 'w', encoding='utf-8') as srt_file:
                srt_file.write('\n'.join(srt_lines))
                
        except Exception as e:
            logger.error(f"VTT to SRT conversion failed: {e}")
            raise
    
    def cleanup_temp_files(self, title: str):
        """Clean up temporary files"""
        try:
            # Clean up possible temporary files
            for pattern in [f"{title}*.part", f"{title}*.tmp", f"{title}*.ytdl"]:
                for temp_file in self.download_dir.glob(pattern):
                    temp_file.unlink(missing_ok=True)
        except Exception as e:
            logger.warning(f"Failed to clean up temporary files: {e}")

# Convenience function
async def download_bilibili_video(
    url: str, 
    download_dir: Optional[Path] = None,
    browser: Optional[str] = None,
    progress_callback: Optional[Callable[[str, float], None]] = None
) -> Dict[str, str]:
    """
    Convenient Bilibili video download function
    
    Args:
        url: Bilibili video link
        download_dir: Download directory
        browser: Browser type
        progress_callback: Progress callback function
        
    Returns:
        Dictionary containing video_path and subtitle_path
    """
    downloader = BilibiliDownloader(download_dir, browser)
    return await downloader.download_video_and_subtitle(url, progress_callback)

async def get_bilibili_video_info(url: str, browser: Optional[str] = None) -> BilibiliVideoInfo:
    """
    Convenient Bilibili video info retrieval function
    
    Args:
        url: Bilibili video link
        browser: Browser type
        
    Returns:
        Video information object
    """
    downloader = BilibiliDownloader(browser=browser)
    return await downloader.get_video_info(url)
