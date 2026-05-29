"""
Step 4: Title Generation - Generate attractive titles for high-quality content
"""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from collections import defaultdict

# Import dependencies
from ..utils.llm_client import LLMClient
from ..utils.text_processor import TextProcessor
from ..core.shared_config import PROMPT_FILES, METADATA_DIR

logger = logging.getLogger(__name__)

class TitleGenerator:
    """Title Generator"""
    
    def __init__(self, metadata_dir: Optional[Path] = None, prompt_files: Dict = None):
        self.llm_client = LLMClient()
        self.text_processor = TextProcessor()
        
        # Load prompts
        prompt_files_to_use = prompt_files if prompt_files is not None else PROMPT_FILES
        with open(prompt_files_to_use['title'], 'r', encoding='utf-8') as f:
            self.title_prompt = f.read()
        
        # Use passed metadata_dir or default value
        if metadata_dir is None:
            metadata_dir = METADATA_DIR
        self.metadata_dir = metadata_dir
        self.llm_raw_output_dir = self.metadata_dir / "step4_llm_raw_output"
    
    def generate_titles(self, high_score_clips: List[Dict]) -> List[Dict]:
        """
        Generate titles for high-scoring clips (new version: batch processing by chunk with caching)
        """
        if not high_score_clips:
            return []
            
        logger.info(f"Starting batch title generation for {len(high_score_clips)} high-scoring clips...")
        
        self.llm_raw_output_dir.mkdir(parents=True, exist_ok=True)
        
        clips_by_chunk = defaultdict(list)
        for clip in high_score_clips:
            clips_by_chunk[clip.get('chunk_index', 0)].append(clip)
            
        all_clips_with_titles = []
        for chunk_index, chunk_clips in clips_by_chunk.items():
            logger.info(f"Processing chunk {chunk_index}, containing {len(chunk_clips)} clips...")
            
            try:
                logger.info(f"  > Starting API call for title generation...")
                input_for_llm = [
                    {
                        "id": clip.get('id'),
                        "title": clip.get('outline'),  # Use outline field as title
                        "content": clip.get('content'),
                        "recommend_reason": clip.get('recommend_reason')
                    } for clip in chunk_clips
                ]
                
                raw_response = self.llm_client.call_with_retry(self.title_prompt, input_for_llm)
                
                if raw_response:
                    # Save LLM raw response for debugging (but not used as cache)
                    llm_cache_path = self.llm_raw_output_dir / f"chunk_{chunk_index}.txt"
                    with open(llm_cache_path, 'w', encoding='utf-8') as f:
                        f.write(raw_response)
                    logger.info(f"  > LLM raw response saved to {llm_cache_path}")
                    titles_map = self.llm_client.parse_json_response(raw_response)
                else:
                    titles_map = {}
                
                if not isinstance(titles_map, dict):
                    logger.warning(f"  > LLM returned titles is not a dict: {titles_map}, skipping this chunk.")
                    # Even if failed, add original clips back to avoid data loss
                    all_clips_with_titles.extend(chunk_clips)
                    continue

                for clip in chunk_clips:
                    clip_id = clip.get('id')
                    generated_title = titles_map.get(clip_id)
                    if generated_title and isinstance(generated_title, str):
                        clip['generated_title'] = generated_title
                        # Safely get outline title for log display
                        outline = clip.get('outline', {})
                        if isinstance(outline, dict):
                            title = outline.get('title', 'Unknown title')
                        else:
                            title = str(outline)
                        logger.info(f"  > Generated title for clip {clip_id} ('{title[:20]}...'): {generated_title}")
                    else:
                        clip['generated_title'] = clip.get('outline', f"Clip_{clip_id}")  # Use outline as fallback
                        logger.warning(f"  > Failed to find or parse title for clip {clip_id}, using original outline")
                
                all_clips_with_titles.extend(chunk_clips)

            except Exception as e:
                logger.error(f"  > Error generating titles for chunk {chunk_index}: {e}")
                # Even on error, add original data to prevent loss
                all_clips_with_titles.extend(chunk_clips)
                continue
                
        logger.info("All high-scoring clip title generation completed")
        return all_clips_with_titles
        
    def save_clips_with_titles(self, clips_with_titles: List[Dict], output_path: Path):
        """Save clip data with titles"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clips_with_titles, f, ensure_ascii=False, indent=2)
        logger.info(f"Clip data with titles saved to: {output_path}")

def run_step4_title(high_score_clips_path: Path, output_path: Optional[Path] = None, metadata_dir: Optional[str] = None, prompt_files: Dict = None) -> List[Dict]:
    """
    Run Step 4: Title Generation
    
    Args:
        high_score_clips_path: High-scoring clips file path
        output_path: Output file path, defaults to step4_titles.json
        metadata_dir: Metadata directory path
        prompt_files: Custom prompt files
        
    Returns:
        List of clips with titles
        
    Note:
        This step only saves step4_titles.json file containing clip data with titles.
        The clips_metadata.json file will be saved in step6 to avoid duplicate saving.
    """
    # Load high-scoring clips
    with open(high_score_clips_path, 'r', encoding='utf-8') as f:
        high_score_clips = json.load(f)
        
    # Create title generator
    if metadata_dir is None:
        metadata_dir = METADATA_DIR
    title_generator = TitleGenerator(metadata_dir=Path(metadata_dir), prompt_files=prompt_files)
    
    # Generate titles
    clips_with_titles = title_generator.generate_titles(high_score_clips)
    
    # Determine output path
    if metadata_dir is None:
        metadata_dir = METADATA_DIR
    
    if output_path is None:
        output_path = Path(metadata_dir) / "step4_titles.json"
        
    # Save clip data with titles to step4_titles.json
    title_generator.save_clips_with_titles(clips_with_titles, output_path)
    
    # Important note: clips_metadata.json will be saved in step6, not duplicated here
    # This avoids data duplication and messy saving logic
    
    return clips_with_titles
