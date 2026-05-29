"""
Step 6: Video Generation - Generate final video clips based on clustering results
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import dependencies
from ..utils.video_processor import VideoProcessor
from ..core.shared_config import METADATA_DIR, CLIPS_DIR, COLLECTIONS_DIR

logger = logging.getLogger(__name__)

class VideoGenerator:
    """Video Generator"""
    
    def __init__(self, clips_dir: Optional[str] = None, collections_dir: Optional[str] = None, metadata_dir: Optional[str] = None):
        if not clips_dir:
            raise ValueError("clips_dir parameter is required, cannot use global path")

        self.clips_dir = Path(clips_dir)
        self.collections_dir = Path(collections_dir) if collections_dir else None
        self.metadata_dir = Path(metadata_dir) if metadata_dir else METADATA_DIR

        self.clips_dir.mkdir(parents=True, exist_ok=True)
        if self.collections_dir is not None:
            self.collections_dir.mkdir(parents=True, exist_ok=True)

        self.video_processor = VideoProcessor(
            clips_dir=str(self.clips_dir),
            collections_dir=str(self.collections_dir) if self.collections_dir else None,
        )
    
    def generate_clips(self, clips_with_titles: List[Dict], input_video: Path) -> List[Path]:
        """
        Generate clip videos
        
        Args:
            clips_with_titles: Clip data with titles
            input_video: Input video path
            
        Returns:
            List of generated clip video paths
        """
        logger.info("Starting clip video generation...")
        
        # Prepare clip data
        clips_data = []
        for clip in clips_with_titles:
            clips_data.append({
                'id': clip['id'],
                'title': clip.get('generated_title', f"Clip_{clip['id']}"),
                'start_time': clip['start_time'],
                'end_time': clip['end_time']
            })
        
        # Batch generate clips
        successful_clips = self.video_processor.batch_extract_clips(input_video, clips_data)
        
        logger.info(f"Clip video generation completed, total {len(successful_clips)} clips")
        return successful_clips
    
    def generate_collections(self, collections_data: List[Dict]) -> List[Path]:
        """
        Generate collection videos
        
        Args:
            collections_data: Collection data
            
        Returns:
            List of generated collection video paths
        """
        logger.info("Starting collection video generation...")
        
        # Generate collection videos
        successful_collections = self.video_processor.create_collections_from_metadata(collections_data)
        
        logger.info(f"Collection video generation completed, total {len(successful_collections)} collections")
        return successful_collections
    
    def save_clip_metadata(self, clips_with_titles: List[Dict], output_path: Optional[Path] = None) -> Path:
        """
        Save final clip metadata to clips_metadata.json
        
        Args:
            clips_with_titles: Clip data with titles (from step4)
            output_path: Output path, defaults to clips_metadata.json
            
        Returns:
            Path to saved file
            
        Note:
            This method saves the final clip metadata containing complete information after video generation.
            Unlike step4's step4_titles.json, this saves the final data for frontend display.
        """
        if output_path is None:
            output_path = self.metadata_dir / "clips_metadata.json"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clips_with_titles, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Clip metadata saved to: {output_path}")
        return output_path
    
    def save_collection_metadata(self, collections_data: List[Dict], output_path: Optional[Path] = None) -> Path:
        """
        Save collection metadata
        
        Args:
            collections_data: Collection data
            output_path: Output path
            
        Returns:
            Path to saved file
        """
        if output_path is None:
            output_path = self.metadata_dir / "collections_metadata.json"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save data
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(collections_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Collection metadata saved to: {output_path}")
        return output_path

def run_step6_video(clips_with_titles_path: Path, collections_path: Path, 
                   input_video: Path, output_dir: Optional[Path] = None, 
                   clips_dir: Optional[str] = None, collections_dir: Optional[str] = None, 
                   metadata_dir: Optional[str] = None) -> Dict:
    """
    Run Step 6: Video Clipping
    
    Args:
        clips_with_titles_path: Clips with titles file path
        collections_path: Collections file path
        input_video: Input video path
        output_dir: Output directory
        
    Returns:
        Generation result information
    """
    # Load data
    with open(clips_with_titles_path, 'r', encoding='utf-8') as f:
        clips_with_titles = json.load(f)
    
    with open(collections_path, 'r', encoding='utf-8') as f:
        collections_data = json.load(f)
    
    # Create video generator
    generator = VideoGenerator(clips_dir=clips_dir, collections_dir=collections_dir, metadata_dir=metadata_dir)
    
    # Generate clip videos (X clipper path: individual clips only, no compilations)
    successful_clips = generator.generate_clips(clips_with_titles, input_video)

    successful_collections: List[Path] = []
    if collections_data:
        successful_collections = generator.generate_collections(collections_data)
    else:
        logger.info("No collections defined; skipping compilation videos (clips only).")

    # Save metadata to project directory
    # Note: clips_metadata.json is saved here, containing final clip metadata (including video paths etc.)
    # This is different from step4's step4_titles.json, which only saves clip data with titles
    if metadata_dir:
        project_metadata_dir = Path(metadata_dir)
        generator.save_clip_metadata(clips_with_titles, project_metadata_dir / "clips_metadata.json")
        if collections_data:
            generator.save_collection_metadata(collections_data, project_metadata_dir / "collections_metadata.json")
    else:
        generator.save_clip_metadata(clips_with_titles)
        if collections_data:
            generator.save_collection_metadata(collections_data)
    
    # Return result information
    result = {
        'clips_generated': len(successful_clips),
        'collections_generated': len(successful_collections),
        'clip_paths': [str(path) for path in successful_clips],
        'collection_paths': [str(path) for path in successful_collections]
    }
    
    logger.info(f"Video generation completed: {result['clips_generated']} clips, {result['collections_generated']} collections")
    
    # Save results to output file
    if output_dir is not None:
        output_path = output_dir / "step6_video_output.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"Step 6 results saved to: {output_path}")
    
    return result
