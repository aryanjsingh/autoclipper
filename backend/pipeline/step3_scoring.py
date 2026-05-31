"""
Step 3: Content Scoring - Score each topic for quality and filter high-quality content
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
from ..core.shared_config import (
    PROMPT_FILES,
    METADATA_DIR,
    MIN_SCORE_THRESHOLD,
    TOP_FALLBACK_CLIP_COUNT,
)

logger = logging.getLogger(__name__)

class ClipScorer:
    """Content Scorer"""
    
    def __init__(self, prompt_files: Dict = None):
        self.llm_client = LLMClient()
        self.text_processor = TextProcessor()
        
        # Load prompts
        prompt_files_to_use = prompt_files if prompt_files is not None else PROMPT_FILES
        with open(prompt_files_to_use['recommendation'], 'r', encoding='utf-8') as f:
            self.recommendation_prompt = f.read()
    
    def score_clips(self, timeline_data: List[Dict]) -> List[Dict]:
        """
        Score clips (new version: batch processing by chunk with LLM comprehensive evaluation)
        """
        if not timeline_data:
            logger.warning("Timeline data is empty, cannot score")
            return []
            
        logger.info(f"Starting batch scoring for {len(timeline_data)} clips...")
        
        # 1. Group all timeline data by chunk_index
        timeline_by_chunk = defaultdict(list)
        for item in timeline_data:
            chunk_index = item.get('chunk_index')
            if chunk_index is not None:
                timeline_by_chunk[chunk_index].append(item)
            else:
                logger.warning(f"  > Topic '{item.get('outline', 'Unknown')}' missing chunk_index, will be skipped.")
        
        all_scored_clips = []
        # 2. Iterate through each chunk, batch process all topics within
        for chunk_index, chunk_items in timeline_by_chunk.items():
            logger.info(f"Processing chunk {chunk_index}, containing {len(chunk_items)} topics...")
            try:
                # 3. Use LLM for batch evaluation
                scored_chunk_items = self._get_llm_evaluation(chunk_items)
                
                if scored_chunk_items:
                    all_scored_clips.extend(scored_chunk_items)
                else:
                    logger.warning(f"LLM evaluation for chunk {chunk_index} returned empty, skipping.")

            except Exception as e:
                logger.error(f"  > Error scoring chunk {chunk_index}: {str(e)}")
                continue

        # 4. Sort all results by final score
        if all_scored_clips:
            all_scored_clips.sort(key=lambda x: x.get('final_score', 0), reverse=True)
            # Keep fixed IDs assigned in Step 2, no longer reassign
            logger.info("Scoring sort completed, keeping original fixed IDs unchanged")
            
            # Final sort by ID to ensure chronological order consistency
            all_scored_clips.sort(key=lambda x: int(x.get('id', 0)))
            logger.info("Sort by ID completed, maintaining chronological order")
                
        logger.info("All clip scoring completed")
        return all_scored_clips
    
    def _get_llm_evaluation(self, clips: List[Dict]) -> List[Dict]:
        """
        Use LLM for batch evaluation, adding final_score and recommend_reason to each clip.
        Results are matched back to clips by `id` (robust to reordering or omissions),
        falling back to positional order only when ids are unavailable.
        """
        try:
            # Send each clip's id so we can match the scores back precisely.
            input_for_llm = [
                {
                    "id": clip.get('id'),
                    "outline": clip.get('outline'),
                    "content": clip.get('content'),
                    "start_time": clip.get('start_time'),
                    "end_time": clip.get('end_time'),
                } for clip in clips
            ]

            response = self.llm_client.call_with_retry(
                self.recommendation_prompt, input_for_llm, pipeline_step="step3"
            )
            parsed_list = self.llm_client.parse_json_response(response)

            if not isinstance(parsed_list, list):
                logger.error(f"LLM scoring returned a non-list response: {type(parsed_list)}")
                return self._mark_failed(clips, "Invalid scoring response")

            # Index results by id when present.
            results_by_id = {}
            for result in parsed_list:
                if isinstance(result, dict) and result.get('id') is not None:
                    results_by_id[str(result['id'])] = result

            use_positional = len(results_by_id) < len(parsed_list)

            for index, clip in enumerate(clips):
                llm_result = None
                clip_id = clip.get('id')
                if clip_id is not None and str(clip_id) in results_by_id:
                    llm_result = results_by_id[str(clip_id)]
                elif use_positional and index < len(parsed_list) and isinstance(parsed_list[index], dict):
                    llm_result = parsed_list[index]

                score = llm_result.get('final_score') if llm_result else None
                reason = llm_result.get('recommend_reason') if llm_result else None

                if score is None:
                    logger.warning(f"No score returned for clip {clip_id}; defaulting to 0.")
                    clip['final_score'] = 0.0
                    clip['recommend_reason'] = reason or "Evaluation failed"
                else:
                    try:
                        clip['final_score'] = round(float(score), 2)
                    except (TypeError, ValueError):
                        clip['final_score'] = 0.0
                    clip['recommend_reason'] = reason or ""
                    outline = clip.get('outline', {})
                    title = outline.get('title', 'Unknown') if isinstance(outline, dict) else str(outline)
                    logger.info(f"  > Scored '{title[:30]}' -> {clip['final_score']}")

            return clips

        except Exception as e:
            logger.error(f"LLM batch evaluation failed: {e}")
            return self._mark_failed(clips, "Batch evaluation failed")

    @staticmethod
    def _mark_failed(clips: List[Dict], reason: str) -> List[Dict]:
        for clip in clips:
            clip['final_score'] = 0.0
            clip['recommend_reason'] = reason
        return clips

    def save_scores(self, scored_clips: List[Dict], output_path: Path):
        """Save scoring results"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(scored_clips, f, ensure_ascii=False, indent=2)
        logger.info(f"Scoring results saved to: {output_path}")


def select_clips_for_pipeline(
    scored_clips: List[Dict],
    threshold: float = MIN_SCORE_THRESHOLD,
    fallback_count: int = TOP_FALLBACK_CLIP_COUNT,
) -> List[Dict]:
    """
    Keep clips at or above threshold. If none qualify, take the top N by score.
    """
    passing = [clip for clip in scored_clips if clip.get('final_score', 0) >= threshold]

    if passing:
        return passing

    if not scored_clips:
        return []

    ranked = sorted(scored_clips, key=lambda clip: clip.get('final_score', 0), reverse=True)
    selected = ranked[:fallback_count]
    logger.info(
        "No clips passed score threshold %.2f; using top %d by score: %s",
        threshold,
        len(selected),
        ", ".join(f"id={c.get('id')} score={c.get('final_score')}" for c in selected),
    )
    return selected


def run_step3_scoring(timeline_path: Path, metadata_dir: Path = None, output_path: Optional[Path] = None, prompt_files: Dict = None) -> List[Dict]:
    """
    Run Step 3: Content Scoring and Filtering
    
    Args:
        timeline_path: Timeline file path
        output_path: Output file path
        prompt_files: Custom prompt files
        
    Returns:
        List of high-scoring clips
    """
    # Load timeline data
    with open(timeline_path, 'r', encoding='utf-8') as f:
        timeline_data = json.load(f)
    
    # Create scorer
    scorer = ClipScorer(prompt_files)
    
    # Score
    scored_clips = scorer.score_clips(timeline_data)
    
    high_score_clips = select_clips_for_pipeline(scored_clips)
    
    # Save results
    if metadata_dir is None:
        metadata_dir = METADATA_DIR
    
    # Save all scored clips (for debugging and analysis)
    all_scored_path = metadata_dir / "step3_all_scored.json"
    scorer.save_scores(scored_clips, all_scored_path)
    
    # Save filtered high-scoring clips (for subsequent steps)
    if output_path is None:
        output_path = metadata_dir / "step3_high_score_clips.json"
        
    scorer.save_scores(high_score_clips, output_path)
    
    return high_score_clips
