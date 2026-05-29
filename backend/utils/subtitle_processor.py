import logging
import re
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import pysrt
from pysrt import SubRipItem, SubRipTime

logger = logging.getLogger(__name__)

class SubtitleProcessor:
    """Subtitle processor - Supports word-level subtitle parsing and processing"""
    
    def __init__(self):
        # Fix invalid escape sequences in regex, use raw string
        self.word_separators = r'[，。！？；：""''（）【】、\s]+'
    
    def parse_srt_to_word_level(self, srt_path: Path) -> List[Dict]:
        """
        Parse SRT subtitles into word-level data structure
        
        Args:
            srt_path: SRT file path
            
        Returns:
            List of word-level subtitle data
        """
        if not srt_path.exists():
            logger.error(f"SRT file does not exist: {srt_path}")
            return []
        
        try:
            subs = pysrt.open(str(srt_path), encoding='utf-8')
            word_level_data = []
            
            for sub in subs:
                segment_data = self._process_subtitle_segment(sub)
                word_level_data.append(segment_data)
            
            logger.info(f"Successfully parsed SRT file, total {len(word_level_data)} subtitle segments")
            return word_level_data
            
        except Exception as e:
            logger.error(f"Failed to parse SRT file: {e}")
            return []
    
    def _process_subtitle_segment(self, sub: SubRipItem) -> Dict:
        """
        Process a single subtitle segment, decompose it into word-level data
        
        Args:
            sub: pysrt subtitle item
            
        Returns:
            Word-level subtitle data
        """
        # Convert time format
        start_seconds = self._srt_time_to_seconds(sub.start)
        end_seconds = self._srt_time_to_seconds(sub.end)
        
        # Split text into words
        words = self._split_text_to_words(sub.text, start_seconds, end_seconds)
        
        return {
            'id': str(uuid.uuid4()),
            'startTime': start_seconds,
            'endTime': end_seconds,
            'text': sub.text.strip(),
            'words': words,
            'index': sub.index
        }
    
    def _split_text_to_words(self, text: str, start_time: float, end_time: float) -> List[Dict]:
        """
        Split text into words and assign timestamps
        
        Args:
            text: Subtitle text
            start_time: Start time (seconds)
            end_time: End time (seconds)
            
        Returns:
            List of words, each containing timestamps
        """
        # Clean text
        clean_text = text.strip()
        if not clean_text:
            return []
        
        # Split by punctuation and spaces
        word_parts = re.split(self.word_separators, clean_text)
        word_parts = [part.strip() for part in word_parts if part.strip()]
        
        if not word_parts:
            return []
        
        # Calculate time allocation for each word
        total_duration = end_time - start_time
        words_count = len(word_parts)
        
        # Simple time allocation strategy: evenly distribute
        word_duration = total_duration / words_count
        
        words = []
        for i, word_text in enumerate(word_parts):
            word_start = start_time + (i * word_duration)
            word_end = word_start + word_duration
            
            words.append({
                'id': str(uuid.uuid4()),
                'text': word_text,
                'startTime': word_start,
                'endTime': word_end
            })
        
        return words
    
    def _srt_time_to_seconds(self, srt_time: SubRipTime) -> float:
        """
        Convert SRT time format to seconds
        
        Args:
            srt_time: pysrt time object
            
        Returns:
            Seconds
        """
        return srt_time.hours * 3600 + srt_time.minutes * 60 + srt_time.seconds + srt_time.milliseconds / 1000
    
    def _seconds_to_srt_time_object(self, time_str: str) -> SubRipTime:
        """
        Convert time string to pysrt time object
        
        Args:
            time_str: Time string (e.g., "00:01:25,140")
            
        Returns:
            pysrt time object
        """
        # Handle comma and dot formats
        time_str = time_str.replace(',', '.')
        
        # Parse time
        time_parts = time_str.split(':')
        hours = int(time_parts[0])
        minutes = int(time_parts[1])
        
        # Handle seconds and milliseconds
        seconds_part = time_parts[2]
        if '.' in seconds_part:
            seconds, milliseconds = seconds_part.split('.')
            seconds = int(seconds)
            milliseconds = int(milliseconds.ljust(3, '0')[:3])  # Ensure 3-digit milliseconds
        else:
            seconds = int(seconds_part)
            milliseconds = 0
        
        return SubRipTime(hours, minutes, seconds, milliseconds)
    
    def create_edit_operations(self, deleted_segments: List[str], 
                             original_data: List[Dict]) -> List[Dict]:
        """
        Create edit operations based on deleted subtitle segments
        
        Args:
            deleted_segments: List of subtitle segment IDs to delete
            original_data: Original subtitle data
            
        Returns:
            List of edit operations
        """
        operations = []
        
        for segment_id in deleted_segments:
            segment = next((s for s in original_data if s['id'] == segment_id), None)
            if segment:
                operation = {
                    'type': 'delete',
                    'segmentIds': [segment_id],
                    'timestamp': segment['startTime'],
                    'metadata': {
                        'originalText': segment['text'],
                        'timeRange': {
                            'start': segment['startTime'],
                            'end': segment['endTime']
                        }
                    }
                }
                operations.append(operation)
        
        return operations
    
    def generate_edited_video_timeline(self, original_data: List[Dict], 
                                     deleted_segments: List[str]) -> List[Tuple[float, float]]:
        """
        Generate edited video timeline
        
        Args:
            original_data: Original subtitle data
            deleted_segments: List of subtitle segment IDs to delete
            
        Returns:
            List of retained segment time ranges [(start, end), ...]
        """
        deleted_ids = set(deleted_segments)
        timeline = []
        
        for segment in original_data:
            if segment['id'] not in deleted_ids:
                timeline.append((segment['startTime'], segment['endTime']))
        
        # Merge adjacent time segments
        if timeline:
            merged_timeline = [timeline[0]]
            for current_start, current_end in timeline[1:]:
                last_start, last_end = merged_timeline[-1]
                
                # If current segment is adjacent to or overlaps with previous segment, merge them
                if current_start <= last_end + 0.1:  # Allow 0.1 second gap
                    merged_timeline[-1] = (last_start, max(last_end, current_end))
                else:
                    merged_timeline.append((current_start, current_end))
            
            return merged_timeline
        
        return []
    
    def export_edited_srt(self, original_data: List[Dict], 
                         deleted_segments: List[str], 
                         output_path: Path) -> bool:
        """
        Export edited SRT file
        
        Args:
            original_data: Original subtitle data
            deleted_segments: List of subtitle segment IDs to delete
            output_path: Output file path
            
        Returns:
            Whether successful
        """
        try:
            deleted_ids = set(deleted_segments)
            edited_segments = []
            
            for segment in original_data:
                if segment['id'] not in deleted_ids:
                    edited_segments.append(segment)
            
            # Renumber
            for i, segment in enumerate(edited_segments, 1):
                segment['index'] = i
            
            # Write SRT file
            with open(output_path, 'w', encoding='utf-8') as f:
                for segment in edited_segments:
                    start_time = self._seconds_to_srt_time(segment['startTime'])
                    end_time = self._seconds_to_srt_time(segment['endTime'])
                    
                    f.write(f"{segment['index']}\n")
                    f.write(f"{start_time} --> {end_time}\n")
                    f.write(f"{segment['text']}\n\n")
            
            logger.info(f"Edited SRT file saved: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export edited SRT file: {e}")
            return False
    
    def _seconds_to_srt_time(self, seconds: float) -> str:
        """
        Convert seconds to SRT time format
        
        Args:
            seconds: Seconds
            
        Returns:
            SRT time format string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    def get_subtitle_statistics(self, data: List[Dict]) -> Dict:
        """
        Get subtitle statistics
        
        Args:
            data: Subtitle data
            
        Returns:
            Statistics information
        """
        if not data:
            return {
                'totalDuration': 0,
                'wordCount': 0,
                'segmentCount': 0,
                'averageWordsPerSegment': 0
            }
        
        total_duration = max(seg['endTime'] for seg in data) - min(seg['startTime'] for seg in data)
        word_count = sum(len(seg['words']) for seg in data)
        segment_count = len(data)
        
        return {
            'totalDuration': total_duration,
            'wordCount': word_count,
            'segmentCount': segment_count,
            'averageWordsPerSegment': word_count / segment_count if segment_count > 0 else 0
        }
