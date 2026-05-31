"""
Video processing utility
"""
import subprocess
import json
import logging
import re
from typing import List, Dict, Optional
from pathlib import Path

# Fix import issues
try:
    from ..core.shared_config import CLIPS_DIR, COLLECTIONS_DIR
except ImportError:
    # If relative import fails, try absolute import
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from ..core.shared_config import CLIPS_DIR, COLLECTIONS_DIR

logger = logging.getLogger(__name__)

try:
    from ..core.shared_config import WATERMARK_ENABLED, WATERMARK_USERNAME
except ImportError:
    WATERMARK_ENABLED = True
    WATERMARK_USERNAME = "ARYNNSGH"

from .watermark import apply_watermark, ensure_twitter_compatible

class VideoProcessor:
    """Video processing utility class"""
    
    def __init__(self, clips_dir: Optional[str] = None, collections_dir: Optional[str] = None):
        if not clips_dir:
            raise ValueError("clips_dir parameter is required, cannot use global path")

        self.clips_dir = Path(clips_dir)
        self.collections_dir = Path(collections_dir) if collections_dir else None
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Clean filename, remove or replace illegal characters
        
        Args:
            filename: Original filename
            
        Returns:
            Cleaned filename
        """
        # Remove or replace illegal characters
        # Characters not allowed on both Windows and Unix systems: < > : " | ? * \ /
        # Replace with underscore
        sanitized = re.sub(r'[<>:"|?*\\/]', '_', filename)
        
        # Remove leading/trailing spaces and dots
        sanitized = sanitized.strip(' .')
        
        # Limit length to avoid overly long filenames
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        # Ensure filename is not empty
        if not sanitized:
            sanitized = "untitled"
            
        return sanitized
    
    @staticmethod
    def convert_srt_time_to_ffmpeg_time(srt_time: str) -> str:
        """
        Convert SRT time format to FFmpeg time format
        
        Args:
            srt_time: SRT time format (e.g., "00:00:06,140" or "00:00:06.140")
            
        Returns:
            FFmpeg time format (e.g., "00:00:06.140")
        """
        # Replace comma with dot
        return srt_time.replace(',', '.')
    
    @staticmethod
    def convert_seconds_to_ffmpeg_time(seconds: float) -> str:
        """
        Convert seconds to FFmpeg time format
        
        Args:
            seconds: Seconds
            
        Returns:
            FFmpeg time format (e.g., "00:00:06.140")
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    @staticmethod
    def convert_ffmpeg_time_to_seconds(time_str: str) -> float:
        """
        Convert FFmpeg time format to seconds
        
        Args:
            time_str: FFmpeg time format (e.g., "00:00:06.140")
            
        Returns:
            Seconds
        """
        try:
            # Handle milliseconds part
            if '.' in time_str:
                time_part, ms_part = time_str.split('.')
                milliseconds = int(ms_part)
            else:
                time_part = time_str
                milliseconds = 0
            
            # Parse hours, minutes, seconds
            h, m, s = map(int, time_part.split(':'))
            
            return h * 3600 + m * 60 + s + milliseconds / 1000
        except Exception as e:
            logger.error(f"Time format conversion failed: {time_str}, error: {e}")
            return 0.0
    
    @staticmethod
    def extract_clip(input_video: Path, output_path: Path, 
                    start_time: str, end_time: str) -> bool:
        """
        Extract a segment from video at specified time range
        
        Args:
            input_video: Input video path
            output_path: Output video path
            start_time: Start time (format: "00:01:25,140")
            end_time: End time (format: "00:02:53,500")
            
        Returns:
            Whether successful
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert time format: from SRT format to FFmpeg format
            ffmpeg_start_time = VideoProcessor.convert_srt_time_to_ffmpeg_time(start_time)
            ffmpeg_end_time = VideoProcessor.convert_srt_time_to_ffmpeg_time(end_time)
            
            # Calculate duration
            start_seconds = VideoProcessor.convert_ffmpeg_time_to_seconds(ffmpeg_start_time)
            end_seconds = VideoProcessor.convert_ffmpeg_time_to_seconds(ffmpeg_end_time)
            duration = end_seconds - start_seconds
            
            # Build optimized FFmpeg command
            # Use -ss before input for precise positioning, use -t to specify duration
            cmd = [
                'ffmpeg',
                '-ss', ffmpeg_start_time,  # Position before input, more precise
                '-i', str(input_video),
                '-t', str(duration),  # Use duration instead of absolute end time
                '-c:v', 'copy',  # Copy video stream
                '-c:a', 'copy',  # Copy audio stream
                '-avoid_negative_ts', 'make_zero',
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                logger.info(f"Successfully extracted video clip: {output_path} ({ffmpeg_start_time} -> {ffmpeg_end_time}, duration: {duration:.2f} seconds)")
                return True
            else:
                logger.error(f"Failed to extract video clip: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Video processing exception: {str(e)}")
            return False
    
    @staticmethod
    def create_collection(clips_list: List[Path], output_path: Path) -> bool:
        """
        Concatenate multiple video clips into a collection
        
        Args:
            clips_list: List of video clip paths
            output_path: Output collection path
            
        Returns:
            Whether successful
        """
        try:
            # Validate input parameters
            if not clips_list:
                logger.error("clips_list is empty, cannot create collection")
                return False
            
            # Validate all video files exist
            valid_clips = []
            for clip_path in clips_list:
                if not clip_path.exists():
                    logger.warning(f"Video file does not exist, skipping: {clip_path}")
                    continue
                valid_clips.append(clip_path)
            
            if not valid_clips:
                logger.error("No valid video files, cannot create collection")
                return False
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create concat file
            concat_file = output_path.parent / "concat_list.txt"
            
            with open(concat_file, 'w', encoding='utf-8') as f:
                for clip_path in valid_clips:
                    # Use absolute path and escape single quotes
                    abs_path = clip_path.absolute()
                    escaped_path = str(abs_path).replace("'", "'\"'\"'")
                    f.write(f"file '{escaped_path}'\n")
            
            # Validate concat file content
            if concat_file.stat().st_size == 0:
                logger.error("Concat file is empty, cannot create collection")
                concat_file.unlink(missing_ok=True)
                return False
            
            # Build FFmpeg command - Use H.264 encoding for compatibility
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c:v', 'libx264',  # Use H.264 video encoding
                '-preset', 'ultrafast',  # Use fastest encoding preset
                '-crf', '28',  # Slightly reduce quality for faster encoding
                '-c:a', 'aac',  # Use AAC audio encoding
                '-b:a', '128k',  # Audio bitrate
                '-movflags', '+faststart',  # Optimize for web playback
                '-y',
                str(output_path)
            ]
            
            logger.info(f"Executing FFmpeg command: {' '.join(cmd)}")
            
            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            # Clean up temporary file
            concat_file.unlink(missing_ok=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully created collection: {output_path}")
                return True
            else:
                logger.error(f"Failed to create collection: {result.stderr}")
                logger.error(f"FFmpeg stdout: {result.stdout}")
                return False
                
        except Exception as e:
            logger.error(f"Video concatenation exception: {str(e)}")
            return False
    
    @staticmethod
    def extract_thumbnail(video_path: Path, output_path: Path, time_offset: int = 5) -> bool:
        """
        Extract thumbnail from video
        
        Args:
            video_path: Video file path
            output_path: Output thumbnail path
            time_offset: Extraction time point (seconds)
            
        Returns:
            Whether successful
        """
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build FFmpeg command
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-ss', str(time_offset),
                '-vframes', '1',
                '-q:v', '2',  # High quality
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0 and output_path.exists():
                logger.info(f"Successfully extracted thumbnail: {output_path}")
                return True
            else:
                logger.error(f"Failed to extract thumbnail: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Extract thumbnail exception: {str(e)}")
            return False
    
    @staticmethod
    def get_video_info(video_path: Path) -> Dict:
        """
        Get video information
        
        Args:
            video_path: Video file path
            
        Returns:
            Video information dictionary
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                return {
                    'duration': float(info['format']['duration']),
                    'size': int(info['format']['size']),
                    'bitrate': int(info['format']['bit_rate']),
                    'streams': info['streams']
                }
            else:
                logger.error(f"Failed to get video info: {result.stderr}")
                return {}
                
        except Exception as e:
            logger.error(f"Get video info exception: {str(e)}")
            return {}
    
    def batch_extract_clips(self, input_video: Path, clips_data: List[Dict]) -> List[Path]:
        """
        Batch extract video clips
        
        Args:
            input_video: Input video path
            clips_data: List of clip data, each element contains id, title, start_time, end_time
            
        Returns:
            List of successfully extracted clip paths
        """
        successful_clips = []
        
        for clip_data in clips_data:
            clip_id = clip_data['id']
            title = clip_data.get('title', f"clip_{clip_id}")
            start_time = clip_data['start_time']
            end_time = clip_data['end_time']
            
            # Handle time format - if seconds, convert to SRT format
            if isinstance(start_time, (int, float)):
                start_time = VideoProcessor.convert_seconds_to_ffmpeg_time(start_time)
            if isinstance(end_time, (int, float)):
                end_time = VideoProcessor.convert_seconds_to_ffmpeg_time(end_time)
            
            # Use title as filename and clean illegal characters
            # Include clip_id in filename for easy lookup during collection concatenation
            safe_title = VideoProcessor.sanitize_filename(title)
            output_path = self.clips_dir / f"{clip_id}_{safe_title}.mp4"
            
            logger.info(f"Extracting clip {clip_id}: {start_time} -> {end_time}, output: {output_path}")
            
            if VideoProcessor.extract_clip(input_video, output_path, start_time, end_time):
                # apply_watermark re-encodes to H.264/yuv420p (X-compatible). When
                # the watermark is disabled or fails, the clip is still a stream
                # copy of the source (often yuv444p), which X rejects — so always
                # run the compatibility normalizer as a safety net. It no-ops when
                # the clip is already yuv420p, so marked clips aren't re-encoded.
                if WATERMARK_ENABLED:
                    if not apply_watermark(output_path, username=WATERMARK_USERNAME):
                        logger.warning(f"Clip {clip_id} watermark failed; keeping unmarked clip")
                if not ensure_twitter_compatible(output_path):
                    logger.warning(f"Clip {clip_id} could not be normalized for X; posting may fail")
                successful_clips.append(output_path)
                logger.info(f"Clip {clip_id} extraction succeeded")
            else:
                logger.error(f"Clip {clip_id} extraction failed")
        
        return successful_clips
    
    def create_collections_from_metadata(self, collections_data: List[Dict]) -> List[Path]:
        """
        Create collections based on metadata
        
        Args:
            collections_data: List of collection data
            
        Returns:
            List of successfully created collection paths
        """
        if not collections_data:
            return []
        if self.collections_dir is None:
            raise ValueError("collections_dir is required to build compilation videos")

        successful_collections = []

        for collection_data in collections_data:
            collection_id = collection_data['id']
            collection_title = collection_data.get('collection_title', f'collection_{collection_id}')
            clip_ids = collection_data['clip_ids']
            
            # Build clip path list
            clips_list = []
            for clip_id in clip_ids:
                # Find corresponding clip file
                # New filename format is: {clip_id}_{title}.mp4
                clip_path = self.clips_dir / f"{clip_id}_*.mp4"
                found_clips = list(self.clips_dir.glob(f"{clip_id}_*.mp4"))
                
                if found_clips:
                    found_clip = found_clips[0]  # Take first matching file
                    clips_list.append(found_clip)
                    logger.info(f"Found clip for collection {collection_id}: {found_clip.name}")
                else:
                    logger.warning(f"Clip {clip_id} not found for collection {collection_id}")
            
            if clips_list:
                # Use collection_title as filename and clean illegal characters
                safe_title = VideoProcessor.sanitize_filename(collection_title)
                output_path = self.collections_dir / f"{safe_title}.mp4"
                
                if VideoProcessor.create_collection(clips_list, output_path):
                    successful_collections.append(output_path)
                    logger.info(f"Successfully created collection {collection_id}: {output_path}")
            else:
                logger.warning(f"Collection {collection_id} has no valid clip files found")
        
        return successful_collections
