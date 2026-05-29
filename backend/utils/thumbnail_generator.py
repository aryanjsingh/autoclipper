"""
Video thumbnail generation utility
"""
import subprocess
import logging
from pathlib import Path
from typing import Optional
import base64
from PIL import Image
import io

logger = logging.getLogger(__name__)

class ThumbnailGenerator:
    """Video thumbnail generator"""
    
    def __init__(self):
        self.supported_formats = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
    
    def generate_thumbnail(self, video_path: Path, output_path: Optional[Path] = None, 
                          time_offset: Optional[float] = None, width: int = 320, height: int = 180) -> Optional[Path]:
        """
        Generate video thumbnail - Uses intelligent frame selection strategy
        
        Args:
            video_path: Video file path
            output_path: Output thumbnail path, auto-generated if None
            time_offset: Extraction time point (seconds), auto-selects best time point if None
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            Generated thumbnail path, returns None on failure
        """
        try:
            if not video_path.exists():
                logger.error(f"Video file does not exist: {video_path}")
                return None
            
            # Check file format
            if video_path.suffix.lower() not in self.supported_formats:
                logger.error(f"Unsupported video format: {video_path.suffix}")
                return None
            
            # Generate output path
            if output_path is None:
                output_path = video_path.parent / f"{video_path.stem}_thumbnail.jpg"
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Intelligently select time point
            if time_offset is None:
                time_offset = self._get_optimal_thumbnail_time(video_path)
            
            # Check if using video cover
            if time_offset == -1.0:
                # Use video cover
                cover_path = video_path.parent / f"{video_path.stem}_cover.jpg"
                if cover_path.exists():
                    # Directly copy cover file and resize
                    cmd = [
                        'ffmpeg',
                        '-i', str(cover_path),
                        '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',
                        '-q:v', '2',
                        '-y',
                        str(output_path)
                    ]
                    logger.info(f"Generating thumbnail using video cover: {cover_path} -> {output_path}")
                else:
                    # Cover does not exist, fall back to default time point
                    time_offset = 1.0
                    cmd = [
                        'ffmpeg',
                        '-ss', str(time_offset),
                        '-i', str(video_path),
                        '-vframes', '1',
                        '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',
                        '-q:v', '2',
                        '-y',
                        str(output_path)
                    ]
                    logger.info(f"Cover does not exist, falling back to default time point: {time_offset} seconds")
            else:
                # Use specified time point
                logger.info(f"Selected thumbnail time point for video {video_path.name}: {time_offset} seconds")
                cmd = [
                    'ffmpeg',
                    '-ss', str(time_offset),  # Jump to specified time
                    '-i', str(video_path),    # Input video
                    '-vframes', '1',          # Extract only one frame
                    '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black',  # Scale and center
                    '-q:v', '2',              # High quality
                    '-y',                     # Overwrite output file
                    str(output_path)
                ]
            
            logger.info(f"Generating thumbnail: {video_path} -> {output_path}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                logger.info(f"Thumbnail generation succeeded: {output_path}")
                return output_path
            else:
                logger.error(f"Thumbnail generation failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Thumbnail generation timed out: {video_path}")
            return None
        except Exception as e:
            logger.error(f"Thumbnail generation exception: {e}")
            return None
    
    def _extract_video_cover(self, video_path: Path) -> Optional[Path]:
        """
        Try to extract the video cover image
        
        Args:
            video_path: Video file path
            
        Returns:
            Cover image path, returns None if not found
        """
        try:
            # Check if there is an embedded cover image
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-an',  # Disable audio
                '-vcodec', 'copy',  # Copy video stream
                '-f', 'image2',
                '-vframes', '1',
                '-y',
                str(video_path.parent / f"{video_path.stem}_cover.jpg")
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                cover_path = video_path.parent / f"{video_path.stem}_cover.jpg"
                if cover_path.exists() and cover_path.stat().st_size > 0:
                    logger.info(f"Successfully extracted video cover: {cover_path}")
                    return cover_path
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract video cover: {e}")
            return None
    
    def _get_optimal_thumbnail_time(self, video_path: Path) -> float:
        """
        Intelligently select the best thumbnail time point
        
        Strategy:
        1. Prioritize trying to extract video cover (if exists)
        2. If video is short (<30 seconds), select middle position
        3. If video is medium length (30 seconds - 5 minutes), select 10% position
        4. If video is long (>5 minutes), select 5% position
        5. Avoid selecting beginning and end, as these positions usually have black screens or transitions
        
        Args:
            video_path: Video file path
            
        Returns:
            Best time point (seconds)
        """
        try:
            # First try to extract video cover
            cover_path = self._extract_video_cover(video_path)
            if cover_path:
                logger.info(f"Using video cover as thumbnail: {cover_path}")
                # If cover extraction succeeded, return special value to indicate using cover
                return -1.0  # Special value indicating use cover
            
            # Get video information
            video_info = self.get_video_info(video_path)
            if not video_info:
                logger.warning(f"Unable to get video info, using default time point: {video_path}")
                return 1.0
            
            # Get video duration
            duration = float(video_info.get('format', {}).get('duration', 0))
            if duration <= 0:
                logger.warning(f"Video duration is 0, using default time point: {video_path}")
                return 1.0
            
            logger.info(f"Video duration: {duration} seconds")
            
            # Intelligently select time point
            if duration < 30:
                # Short video: select middle position
                optimal_time = duration * 0.5
            elif duration < 300:  # 5 minutes
                # Medium length: select 10% position, avoid possible black screen at beginning
                optimal_time = duration * 0.1
            else:
                # Long video: select 5% position
                optimal_time = duration * 0.05
            
            # Ensure time point is reasonable (at least 1 second, not exceeding video length)
            optimal_time = max(1.0, min(optimal_time, duration - 1))
            
            logger.info(f"Selected best time point for video {video_path.name}: {optimal_time} seconds (total duration: {duration} seconds)")
            return optimal_time
            
        except Exception as e:
            logger.error(f"Failed to select best time point: {e}")
            return 1.0
    
    def generate_thumbnail_base64(self, video_path: Path, time_offset: Optional[float] = None, 
                                 width: int = 320, height: int = 180) -> Optional[str]:
        """
        Generate thumbnail and return base64 encoding
        
        Args:
            video_path: Video file path
            time_offset: Extraction time point (seconds), auto-selects best time point if None
            width: Thumbnail width
            height: Thumbnail height
            
        Returns:
            Base64 encoded thumbnail data, returns None on failure
        """
        try:
            # Generate temporary thumbnail
            temp_path = video_path.parent / f"temp_thumbnail_{video_path.stem}.jpg"
            thumbnail_path = self.generate_thumbnail(video_path, temp_path, time_offset, width, height)
            
            if thumbnail_path and thumbnail_path.exists():
                # Read image and convert to base64
                with open(thumbnail_path, 'rb') as f:
                    image_data = f.read()
                    base64_data = base64.b64encode(image_data).decode('utf-8')
                
                # Clean up temporary file
                try:
                    temp_path.unlink()
                except:
                    pass
                
                return f"data:image/jpeg;base64,{base64_data}"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to generate base64 thumbnail: {e}")
            return None
    
    def get_video_info(self, video_path: Path) -> Optional[dict]:
        """
        Get video information
        
        Args:
            video_path: Video file path
            
        Returns:
            Video information dictionary, returns None on failure
        """
        try:
            if not video_path.exists():
                return None
            
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                import json
                return json.loads(result.stdout)
            else:
                logger.error(f"Failed to get video info: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Get video info exception: {e}")
            return None

# Convenience function
def generate_project_thumbnail(project_id: str, video_path: Path) -> Optional[str]:
    """
    Generate thumbnail for project
    
    Args:
        project_id: Project ID
        video_path: Video file path
        
    Returns:
        Base64 encoded thumbnail data
    """
    generator = ThumbnailGenerator()
    return generator.generate_thumbnail_base64(video_path)
