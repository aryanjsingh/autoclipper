"""
Simplified pipeline adapter - integrates with the new progress system
"""

import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from backend.core.output_language import is_english, speech_recognition_language
from backend.core.shared_config import get_prompt_files
from backend.services.simple_progress import emit_progress, clear_progress
from backend.pipeline.step1_outline import run_step1_outline
from backend.pipeline.step2_timeline import run_step2_timeline
from backend.pipeline.step3_scoring import run_step3_scoring
from backend.pipeline.step4_title import run_step4_title
from backend.pipeline.step6_video import run_step6_video
# Note: step5 clustering (compilations) is intentionally not used — the X clipper
# produces standalone clips only.

logger = logging.getLogger(__name__)

_PROGRESS_EN = {
    "INGEST_READY": "Source files ready",
    "SUBTITLE_START": "Processing subtitles",
    "SUBTITLE_AI": "Generating subtitles with AI...",
    "SUBTITLE_DONE": "Subtitles ready",
    "ANALYZE_START": "Analyzing content",
    "ANALYZE_TIMELINE": "Timeline extraction complete",
    "ANALYZE_DONE": "Content analysis complete",
    "HIGHLIGHT_START": "Finding highlight clips",
    "HIGHLIGHT_TITLES": "Titles generated",
    "HIGHLIGHT_DONE": "Highlight selection complete",
    "EXPORT_START": "Exporting videos",
    "EXPORT_DONE": "Export complete",
    "DONE_OK": "Processing complete",
    "DONE_FAIL": "Processing failed",
}

_PROGRESS_ZH = {
    "INGEST_READY": "Source files ready",
    "SUBTITLE_START": "Processing subtitles",
    "SUBTITLE_AI": "Generating subtitles with AI...",
    "SUBTITLE_DONE": "Subtitles ready",
    "ANALYZE_START": "Analyzing content",
    "ANALYZE_TIMELINE": "Timeline extraction complete",
    "ANALYZE_DONE": "Content analysis complete",
    "HIGHLIGHT_START": "Finding highlight clips",
    "HIGHLIGHT_TITLES": "Titles generated",
    "HIGHLIGHT_DONE": "Highlight selection complete",
    "EXPORT_START": "Exporting videos",
    "EXPORT_DONE": "Export complete",
    "DONE_OK": "Processing complete",
    "DONE_FAIL": "Processing failed",
}


def _progress_msg(key: str) -> str:
    table = _PROGRESS_EN if is_english() else _PROGRESS_ZH
    return table[key]


def _load_project_category(project_id: str) -> str:
    from backend.core.database import SessionLocal
    from backend.models.project import Project

    db = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.project_type is not None:
            return project.project_type.value
    finally:
        db.close()
    return "default"


class SimplePipelineAdapter:
    """Simplified pipeline adapter using a fixed-stage progress system"""
    
    def __init__(self, project_id: str, task_id: str):
        self.project_id = project_id
        self.task_id = task_id
        
    async def _generate_subtitle_automatically(self, video_path: str, metadata_dir: Path) -> Path:
        """
        Automatically generate subtitle files
        
        Args:
            video_path: Video file path
            metadata_dir: Metadata directory
            
        Returns:
            Path to the generated SRT file, or None if failed
        """
        try:
            logger.info(f"Starting automatic subtitle generation for video {video_path}")
            
            # Update progress
            from backend.services.simple_progress import emit_progress
            emit_progress(self.project_id, "SUBTITLE", _progress_msg("SUBTITLE_AI"), subpercent=25)
            
            # Try using bcut-asr
            try:
                from backend.utils.speech_recognizer import generate_subtitle_for_video
                from pathlib import Path
                
                video_file_path = Path(video_path)
                if not video_file_path.exists():
                    logger.error(f"Video file does not exist: {video_path}")
                    return None
                
                # Generate subtitles using bcut-asr
                logger.info("Attempting to generate subtitles using bcut-asr")
                output_path = metadata_dir / f"{video_file_path.stem}.srt"
                srt_path = generate_subtitle_for_video(
                    video_file_path,
                    output_path=output_path,
                    method="auto",
                    model="base",
                    language=speech_recognition_language(),
                )
                
                if srt_path and srt_path.exists():
                    logger.info(f"bcut-asr subtitle generation successful: {srt_path}")
                    emit_progress(self.project_id, "SUBTITLE", _progress_msg("SUBTITLE_DONE"), subpercent=40)
                    return srt_path
                else:
                    logger.warning("bcut-asr subtitle generation failed")
                    
            except Exception as e:
                logger.warning(f"bcut-asr subtitle generation failed: {e}")
            
            # If bcut-asr fails, try using the Whisper local model
            try:
                logger.info("Attempting to generate subtitles using Whisper local model")
                output_path = metadata_dir / f"{Path(video_path).stem}.srt"
                srt_path = generate_subtitle_for_video(
                    Path(video_path),
                    output_path=output_path,
                    method="whisper_local",
                    model="base",
                    language=speech_recognition_language(),
                )
                
                if srt_path and srt_path.exists():
                    logger.info(f"Whisper subtitle generation successful: {srt_path}")
                    emit_progress(self.project_id, "SUBTITLE", _progress_msg("SUBTITLE_DONE"), subpercent=40)
                    return srt_path
                else:
                    logger.warning("Whisper subtitle generation failed")
                    
            except Exception as e:
                logger.warning(f"Whisper subtitle generation failed: {e}")
            
            logger.error("All ASR methods failed")
            return None
            
        except Exception as e:
            logger.error(f"Error during automatic subtitle generation: {e}")
            return None
        
    async def process_project_sync(self, input_video_path: str, input_srt_path: str) -> Dict[str, Any]:
        """
        Synchronously process a project - uses simplified progress system
        
        Args:
            input_video_path: Input video path
            input_srt_path: Input SRT path
            
        Returns:
            Processing result
        """
        logger.info(f"Starting project processing: {self.project_id}")
        video_category = _load_project_category(self.project_id)
        prompt_files = get_prompt_files(video_category)
        logger.info("Using prompt files for category=%s language=en=%s", video_category, is_english())

        try:
            # Clear previous progress data
            clear_progress(self.project_id)
            
            # Create necessary directory structure - use correct paths
            from backend.core.path_utils import get_project_directory
            project_dir = get_project_directory(self.project_id)
            metadata_dir = project_dir / "metadata"
            output_dir = project_dir / "output"
            metadata_dir.mkdir(parents=True, exist_ok=True)
            output_dir.mkdir(parents=True, exist_ok=True)
            # Project-specific output subdirectories
            clips_output_dir = output_dir / "clips"
            collections_output_dir = output_dir / "collections"
            clips_output_dir.mkdir(parents=True, exist_ok=True)
            collections_output_dir.mkdir(parents=True, exist_ok=True)
            
            # Stage 1: Source preparation
            emit_progress(self.project_id, "INGEST", _progress_msg("INGEST_READY"))
            
            # Stage 2: Subtitle processing
            emit_progress(self.project_id, "SUBTITLE", _progress_msg("SUBTITLE_START"))
            
            # Step 1: Outline extraction
            logger.info("Executing Step 1: Outline extraction")
            effective_srt_path = None
            if input_srt_path and Path(input_srt_path).exists():
                logger.info(f"Using existing SRT file: {input_srt_path}")
                effective_srt_path = Path(input_srt_path)
                outlines = run_step1_outline(
                    Path(input_srt_path), metadata_dir=metadata_dir, prompt_files=prompt_files
                )
            else:
                logger.warning("No SRT file found, attempting automatic subtitle generation")
                # Try automatic subtitle generation
                srt_path = await self._generate_subtitle_automatically(input_video_path, metadata_dir)
                if srt_path and srt_path.exists():
                    logger.info(f"Automatic subtitle generation successful: {srt_path}")
                    effective_srt_path = srt_path
                    outlines = run_step1_outline(
                        srt_path, metadata_dir=metadata_dir, prompt_files=prompt_files
                    )
                else:
                    logger.warning("Automatic subtitle generation failed, creating empty outline")
                    # Create an empty outline file
                    outlines = []
                    outline_file = metadata_dir / "step1_outline.json"
                    import json
                    with open(outline_file, 'w', encoding='utf-8') as f:
                        json.dump(outlines, f, ensure_ascii=False, indent=2)
            emit_progress(self.project_id, "SUBTITLE", _progress_msg("SUBTITLE_DONE"), subpercent=50)
            
            # Stage 3: Content analysis
            emit_progress(self.project_id, "ANALYZE", _progress_msg("ANALYZE_START"))
            
            # Step 2: Timeline extraction
            logger.info("Executing Step 2: Timeline extraction")
            if outlines:  # Only execute subsequent steps if there are outlines
                timeline_data = run_step2_timeline(
                    metadata_dir / "step1_outline.json",
                    metadata_dir=metadata_dir,
                    prompt_files=prompt_files,
                )
                emit_progress(self.project_id, "ANALYZE", _progress_msg("ANALYZE_TIMELINE"), subpercent=50)
                
                # Step 3: Content scoring
                logger.info("Executing Step 3: Content scoring")
                scored_clips = run_step3_scoring(
                    metadata_dir / "step2_timeline.json",
                    metadata_dir=metadata_dir,
                    prompt_files=prompt_files,
                )
                emit_progress(self.project_id, "ANALYZE", _progress_msg("ANALYZE_DONE"), subpercent=100)
            else:
                logger.warning("No outline data, skipping timeline extraction and content scoring")
                # Create empty timeline and scoring files
                timeline_file = metadata_dir / "step2_timeline.json"
                scored_file = metadata_dir / "step3_high_score_clips.json"
                import json
                with open(timeline_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                with open(scored_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                # Initialize empty variables
                timeline_data = []
                scored_clips = []
                emit_progress(self.project_id, "ANALYZE", _progress_msg("ANALYZE_DONE"), subpercent=100)
            
            # Stage 4: Highlight selection
            emit_progress(self.project_id, "HIGHLIGHT", _progress_msg("HIGHLIGHT_START"))
            
            # Step 4: Title generation
            logger.info("Executing Step 4: Title generation")
            if outlines:  # Only execute subsequent steps if there are outlines
                titled_clips = run_step4_title(
                    metadata_dir / "step3_high_score_clips.json",
                    metadata_dir=str(metadata_dir),
                    prompt_files=prompt_files,
                )
                emit_progress(self.project_id, "HIGHLIGHT", _progress_msg("HIGHLIGHT_TITLES"), subpercent=60)

                # Caption generation: write an X (Twitter) caption for each clip.
                # (Compilations/collections are intentionally disabled for the X clipper.)
                logger.info("Executing caption generation (yonann-style tweet text)")
                from backend.pipeline.step_caption import run_step_caption
                titled_clips = run_step_caption(
                    metadata_dir / "step4_titles.json",
                    effective_srt_path,
                    metadata_dir=metadata_dir,
                    prompt_files=prompt_files,
                )
                # No collections: write an empty collections file for downstream compatibility.
                collections = []
                import json
                with open(metadata_dir / "step5_collections.json", 'w', encoding='utf-8') as f:
                    json.dump(collections, f, ensure_ascii=False, indent=2)
                emit_progress(self.project_id, "HIGHLIGHT", _progress_msg("HIGHLIGHT_DONE"), subpercent=100)

                # Stage 5: Video export
                emit_progress(self.project_id, "EXPORT", _progress_msg("EXPORT_START"))

                # Step 6: Video cutting (clips only, no collection videos)
                logger.info("Executing Step 6: Video cutting")
                video_result = run_step6_video(
                    metadata_dir / "step4_titles.json",
                    metadata_dir / "step5_collections.json",
                    input_video_path,
                    output_dir=output_dir,
                    clips_dir=str(clips_output_dir),
                    collections_dir=str(collections_output_dir),
                    metadata_dir=str(metadata_dir)
                )
            else:
                logger.warning("No outline data, skipping title generation, topic clustering, and video cutting")
                # Create empty title and collection files
                titles_file = metadata_dir / "step4_titles.json"
                collections_file = metadata_dir / "step5_collections.json"
                import json
                with open(titles_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                with open(collections_file, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False, indent=2)
                # Initialize empty variables
                titled_clips = []
                collections = []
                emit_progress(self.project_id, "HIGHLIGHT", _progress_msg("HIGHLIGHT_DONE"), subpercent=100)
                emit_progress(self.project_id, "EXPORT", _progress_msg("EXPORT_START"))
                video_result = {"status": "skipped", "message": "No content to process"}
            emit_progress(self.project_id, "EXPORT", _progress_msg("EXPORT_DONE"), subpercent=100)
            
            # Stage 6: Processing complete
            emit_progress(self.project_id, "DONE", _progress_msg("DONE_OK"))
            
            # Automatically sync data to database
            try:
                from backend.services.data_sync_service import DataSyncService
                from backend.core.database import SessionLocal
                
                db = SessionLocal()
                try:
                    sync_service = DataSyncService(db)
                    sync_result = sync_service.sync_project_from_filesystem(self.project_id, project_dir)
                    if sync_result.get("success"):
                        logger.info(f"Project {self.project_id} data sync successful: {sync_result}")
                    else:
                        logger.error(f"Project {self.project_id} data sync failed: {sync_result}")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Data sync failed: {e}")
            
            logger.info(f"Project processing complete: {self.project_id}")
            return {
                "status": "succeeded",
                "project_id": self.project_id,
                "task_id": self.task_id,
                "result": {
                    "outlines": outlines,
                    "timeline": timeline_data,
                    "scored_clips": scored_clips,
                    "titled_clips": titled_clips,
                    "collections": collections,
                    "video_result": video_result
                }
            }
            
        except Exception as e:
            error_msg = f"Pipeline processing failed: {str(e)}"
            logger.error(error_msg)
            
            # Send failure status
            emit_progress(self.project_id, "DONE", f"{_progress_msg('DONE_FAIL')}: {error_msg}")
            
            return {
                "status": "failed",
                "project_id": self.project_id,
                "task_id": self.task_id,
                "error": error_msg
            }


def create_simple_pipeline_adapter(project_id: str, task_id: str) -> SimplePipelineAdapter:
    """Create a simplified pipeline adapter instance"""
    return SimplePipelineAdapter(project_id, task_id)
