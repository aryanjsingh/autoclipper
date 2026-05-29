"""
Pipeline Adapter
Responsible for coordinating the 6-step pipeline processing flow,
providing a unified interface
"""

import logging
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from sqlalchemy.orm import Session

from ..core.database import SessionLocal
from ..models.project import Project
from ..models.task import Task, TaskStatus
from ..core.shared_config import config_manager, get_prompt_files
from ..pipeline.step1_outline import run_step1_outline
from ..pipeline.step2_timeline import run_step2_timeline
from ..pipeline.step3_scoring import run_step3_scoring
from ..pipeline.step4_title import run_step4_title
from ..pipeline.step5_clustering import run_step5_clustering
from ..pipeline.step6_video import run_step6_video

logger = logging.getLogger(__name__)

class PipelineAdapter:
    """Pipeline adapter"""
    
    def __init__(self, project_id: str, task_id: str, db: Session, progress_callback: Optional[Callable] = None):
        self.project_id = project_id
        self.task_id = task_id
        self.db = db
        self.progress_callback = progress_callback
        
        # Get project configuration
        self.config = config_manager.get_processing_config()
        self.path_config = config_manager.get_path_config()
        
        # Project paths
        self.project_paths = config_manager.get_project_paths(project_id)
        
        # Ensure project directory exists
        config_manager.ensure_project_directories(project_id)
        
        # Step execution results
        self.step_results = {}

    def _get_video_category(self) -> str:
        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        if project and project.project_type is not None:
            return project.project_type.value
        if project and project.project_metadata:
            return project.project_metadata.get("video_category", "default")
        return "default"
        
    def validate_pipeline_prerequisites(self) -> List[str]:
        """
        Validate pipeline prerequisites
        
        Returns:
            List of errors, empty list means validation passed
        """
        errors = []
        
        # Check API key
        api_config = config_manager.get_api_config()
        if not api_config.api_key:
            errors.append("Missing API key configuration")
        
        # Check project directory
        if not self.project_paths["project_base"].exists():
            errors.append(f"Project directory does not exist: {self.project_paths['project_base']}")
        
        # Check input files
        input_video = self.project_paths["input_dir"] / "input.mp4"
        input_srt = self.project_paths["input_dir"] / "input.srt"
        
        if not input_video.exists():
            errors.append(f"Video file does not exist: {input_video}")
        
        if not input_srt.exists():
            errors.append(f"Subtitle file does not exist: {input_srt}")
        
        # Check prompt files
        prompt_files = get_prompt_files()
        for key, path in prompt_files.items():
            if not path.exists():
                errors.append(f"Prompt file does not exist: {path}")
        
        return errors
    
    async def process_project(self, input_video_path: str, input_srt_path: str) -> Dict[str, Any]:
        """
        Process project - async version
        
        Args:
            input_video_path: Input video path
            input_srt_path: Input subtitle path
            
        Returns:
            Processing result
        """
        try:
            logger.info(f"Starting to process project {self.project_id}")
            
            # Validate prerequisites
            errors = self.validate_pipeline_prerequisites()
            if errors:
                error_msg = "; ".join(errors)
                logger.error(f"Pipeline prerequisite validation failed: {error_msg}")
                return {"status": "failed", "message": error_msg}
            
            # Execute 6-step pipeline
            steps = [
                ("step1_outline", "Outline extraction", self._execute_step1),
                ("step2_timeline", "Timeline extraction", self._execute_step2),
                ("step3_scoring", "Content scoring", self._execute_step3),
                ("step4_title", "Title generation", self._execute_step4),
                ("step5_clustering", "Topic clustering", self._execute_step5),
                ("step6_video", "Video generation", self._execute_step6)
            ]
            
            total_steps = len(steps)
            
            for i, (step_name, step_desc, step_func) in enumerate(steps):
                try:
                    logger.info(f"Executing step {i+1}/{total_steps}: {step_desc}")
                    
                    # Update progress - step start
                    progress = int((i / total_steps) * 100)
                    await self._update_progress(progress, f"Starting: {step_desc}")
                    
                    # Execute step
                    result = await step_func()
                    
                    if result.get("status") == "failed":
                        error_msg = result.get("message", "Step execution failed")
                        logger.error(f"Step {step_name} execution failed: {error_msg}")
                        return {"status": "failed", "message": f"{step_desc} failed: {error_msg}"}
                    
                    # Save step result
                    self.step_results[step_name] = result
                    logger.info(f"Step {step_name} executed successfully")
                    
                    # Update progress - step complete
                    progress = int(((i + 1) / total_steps) * 100)
                    await self._update_progress(progress, f"Completed: {step_desc}")
                    
                except Exception as e:
                    error_msg = f"Step {step_name} execution exception: {str(e)}"
                    logger.error(error_msg)
                    return {"status": "failed", "message": error_msg}
            
            # Update final progress
            await self._update_progress(100, "Processing complete")
            
            # Save results to database
            await self._save_results_to_database()
            
            logger.info(f"Project {self.project_id} processing complete")
            return {
                "status": "success",
                "message": "Project processing complete",
                "project_id": self.project_id,
                "results": self.step_results
            }
            
        except Exception as e:
            error_msg = f"Project processing failed: {str(e)}"
            logger.error(error_msg)
            return {"status": "failed", "message": error_msg}
    
    def process_project_sync(self, input_video_path: str, input_srt_path: str) -> Dict[str, Any]:
        """
        Process project - sync version
        
        Args:
            input_video_path: Input video path
            input_srt_path: Input subtitle path
            
        Returns:
            Processing result
        """
        try:
            # Try to get existing event loop
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                # If event loop is closed, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # If no event loop exists, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(self.process_project(input_video_path, input_srt_path))
        finally:
            # Don't close the event loop, let Celery manage it
            pass
    
    async def _execute_step1(self) -> Dict[str, Any]:
        """Execute step 1: Outline extraction"""
        try:
            input_srt_path = self.project_paths["input_dir"] / "input.srt"
            output_path = self.project_paths["metadata_dir"] / "step1_outlines.json"
            
            prompt_files = get_prompt_files(self._get_video_category())
            
            result = run_step1_outline(
                srt_path=input_srt_path,
                metadata_dir=self.project_paths["metadata_dir"],
                output_path=output_path,
                prompt_files=prompt_files
            )
            
            return {"status": "success", "result": result, "output_path": str(output_path)}
            
        except Exception as e:
            logger.error(f"Step 1 execution failed: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _execute_step2(self) -> Dict[str, Any]:
        """Execute step 2: Timeline extraction"""
        try:
            outline_path = self.project_paths["metadata_dir"] / "step1_outlines.json"
            output_path = self.project_paths["metadata_dir"] / "step2_timeline.json"
            
            if not outline_path.exists():
                return {"status": "failed", "message": "Step 1 result file does not exist"}
            
            prompt_files = get_prompt_files(self._get_video_category())
            
            result = run_step2_timeline(
                outline_path=outline_path,
                metadata_dir=self.project_paths["metadata_dir"],
                output_path=output_path,
                prompt_files=prompt_files
            )
            
            return {"status": "success", "result": result, "output_path": str(output_path)}
            
        except Exception as e:
            logger.error(f"Step 2 execution failed: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _execute_step3(self) -> Dict[str, Any]:
        """Execute step 3: Content scoring"""
        try:
            timeline_path = self.project_paths["metadata_dir"] / "step2_timeline.json"
            output_path = self.project_paths["metadata_dir"] / "step3_scoring.json"
            
            if not timeline_path.exists():
                return {"status": "failed", "message": "Step 2 result file does not exist"}
            
            prompt_files = get_prompt_files(self._get_video_category())
            
            result = run_step3_scoring(
                timeline_path=timeline_path,
                metadata_dir=self.project_paths["metadata_dir"],
                output_path=output_path,
                prompt_files=prompt_files
            )
            
            return {"status": "success", "result": result, "output_path": str(output_path)}
            
        except Exception as e:
            logger.error(f"Step 3 execution failed: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _execute_step4(self) -> Dict[str, Any]:
        """Execute step 4: Title generation"""
        try:
            scoring_path = self.project_paths["metadata_dir"] / "step3_scoring.json"
            output_path = self.project_paths["metadata_dir"] / "step4_titles.json"
            
            if not scoring_path.exists():
                return {"status": "failed", "message": "Step 3 result file does not exist"}
            
            prompt_files = get_prompt_files(self._get_video_category())
            
            result = run_step4_title(
                high_score_clips_path=scoring_path,
                metadata_dir=self.project_paths["metadata_dir"],
                output_path=output_path,
                prompt_files=prompt_files
            )
            
            return {"status": "success", "result": result, "output_path": str(output_path)}
            
        except Exception as e:
            logger.error(f"Step 4 execution failed: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _execute_step5(self) -> Dict[str, Any]:
        """Execute step 5: Topic clustering"""
        try:
            titles_path = self.project_paths["metadata_dir"] / "step4_titles.json"
            output_path = self.project_paths["metadata_dir"] / "step5_collections.json"
            
            if not titles_path.exists():
                return {"status": "failed", "message": "Step 4 result file does not exist"}
            
            prompt_files = get_prompt_files(self._get_video_category())
            
            result = run_step5_clustering(
                clips_with_titles_path=titles_path,
                output_path=output_path,
                metadata_dir=self.project_paths["metadata_dir"],
                prompt_files=prompt_files
            )
            
            return {"status": "success", "result": result, "output_path": str(output_path)}
            
        except Exception as e:
            logger.error(f"Step 5 execution failed: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _execute_step6(self) -> Dict[str, Any]:
        """Execute step 6: Video generation"""
        try:
            titles_path = self.project_paths["metadata_dir"] / "step4_titles.json"
            collections_path = self.project_paths["metadata_dir"] / "step5_collections.json"
            input_video_path = self.project_paths["input_dir"] / "input.mp4"
            
            if not titles_path.exists():
                return {"status": "failed", "message": "Step 4 result file does not exist"}
            if not collections_path.exists():
                return {"status": "failed", "message": "Step 5 result file does not exist"}
            if not input_video_path.exists():
                return {"status": "failed", "message": "Input video file does not exist"}
            
            result = run_step6_video(
                clips_with_titles_path=titles_path,
                collections_path=collections_path,
                input_video=input_video_path,
                output_dir=self.project_paths["output_dir"],
                clips_dir=str(self.project_paths["clips_dir"]),
                collections_dir=str(self.project_paths["collections_dir"]),
                metadata_dir=self.project_paths["metadata_dir"]
            )
            
            return {"status": "success", "result": result}
            
        except Exception as e:
            logger.error(f"Step 6 execution failed: {e}")
            return {"status": "failed", "message": str(e)}
    
    async def _update_progress(self, progress: int, message: str):
        """Update progress"""
        try:
            # Update task progress in database
            task = self.db.query(Task).filter(Task.id == self.task_id).first()
            if task:
                task.progress = progress
                task.current_step = message
                task.updated_at = datetime.utcnow()
                self.db.commit()
                logger.info(f"Task {self.task_id} progress updated: {progress}% - {message}")
            
            # Call progress callback
            if self.progress_callback:
                try:
                    # Check if callback function is async
                    import asyncio
                    if asyncio.iscoroutinefunction(self.progress_callback):
                        await self.progress_callback(self.project_id, progress, message)
                    else:
                        # Sync callback function - note parameter order: project_id, progress, message
                        self.progress_callback(self.project_id, progress, message)
                except Exception as callback_error:
                    logger.error(f"Progress callback execution failed: {callback_error}")
                
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
            import traceback
            logger.error(f"Error details: {traceback.format_exc()}")
    
    async def _save_results_to_database(self):
        """Save results to database"""
        try:
            # Update project status
            project = self.db.query(Project).filter(Project.id == self.project_id).first()
            if project:
                project.status = "completed"
                self.db.commit()
                logger.info(f"Project {self.project_id} status updated to completed")
            
            # Sync clips and collections data to database
            await self._sync_clips_and_collections_to_database()
                
        except Exception as e:
            logger.error(f"Failed to save results to database: {e}")
    
    async def _sync_clips_and_collections_to_database(self):
        """Sync clips and collections data to database"""
        try:
            from ..models.clip import Clip, ClipStatus
            from ..models.collection import Collection, CollectionStatus
            from datetime import datetime
            
            # Clean up existing data
            self.db.query(Clip).filter(Clip.project_id == self.project_id).delete()
            self.db.query(Collection).filter(Collection.project_id == self.project_id).delete()
            
            # Sync clips data
            clips_metadata_file = self.project_paths["metadata_dir"] / "clips_metadata.json"
            if clips_metadata_file.exists():
                with open(clips_metadata_file, 'r', encoding='utf-8') as f:
                    clips_data = json.load(f)
                
                clips_count = 0
                for clip_data in clips_data:
                    try:
                        # Build clip file path
                        clip_filename = f"{clip_data['id']}_{clip_data['generated_title']}.mp4"
                        clip_path = self.project_paths["clips_dir"] / clip_filename
                        
                        if not clip_path.exists():
                            continue
                        
                        # Calculate duration
                        start_time_str = clip_data.get('start_time', '00:00:00,000')
                        end_time_str = clip_data.get('end_time', '00:00:00,000')
                        start_seconds = self._parse_time(start_time_str)
                        end_seconds = self._parse_time(end_time_str)
                        duration = end_seconds - start_seconds
                        
                        # Create clip record
                        clip = Clip(
                            id=f"{self.project_id}_{clip_data['id']}",
                            project_id=self.project_id,
                            title=clip_data['generated_title'],
                            description=clip_data.get('recommend_reason', ''),
                            start_time=int(start_seconds),
                            end_time=int(end_seconds),
                            duration=int(duration),
                            video_path=str(clip_path),
                            score=clip_data.get('final_score', 0),
                            recommendation_reason=clip_data.get('recommend_reason', ''),
                            status=ClipStatus.COMPLETED,
                            clip_metadata={
                                'outline': clip_data.get('outline', ''),
                                'content': clip_data.get('content', []),
                                'chunk_index': clip_data.get('chunk_index', 0)
                            },
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        self.db.add(clip)
                        clips_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to sync clip: {e}")
                        continue
                
                logger.info(f"Synced {clips_count} clips to database")
            
            # Sync collections data
            collections_metadata_file = self.project_paths["metadata_dir"] / "collections_metadata.json"
            if collections_metadata_file.exists():
                with open(collections_metadata_file, 'r', encoding='utf-8') as f:
                    collections_data = json.load(f)
                
                collections_count = 0
                for collection_data in collections_data:
                    try:
                        # Build collection file path
                        collection_filename = f"{collection_data['collection_title']}.mp4"
                        collection_path = self.project_paths["collections_dir"] / collection_filename
                        
                        if not collection_path.exists():
                            continue
                        
                        # Convert simplified clip_ids to full clip IDs
                        simplified_clip_ids = collection_data.get('clip_ids', [])
                        full_clip_ids = []
                        for clip_id in simplified_clip_ids:
                            full_clip_id = f"{self.project_id}_{clip_id}"
                            full_clip_ids.append(full_clip_id)
                        
                        # Create collection record
                        collection = Collection(
                            id=f"{self.project_id}_collection_{collection_data['id']}",
                            project_id=self.project_id,
                            name=collection_data['collection_title'],
                            description=collection_data.get('collection_summary', ''),
                            theme="Investment",
                            status=CollectionStatus.COMPLETED,
                            tags=["Investment", "Finance", "Strategy"],
                            collection_metadata={
                                'clip_ids': full_clip_ids,  # Use full clip IDs
                                'simplified_clip_ids': simplified_clip_ids,  # Keep original simplified IDs
                                'generated_by': 'pipeline'
                            },
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        
                        self.db.add(collection)
                        collections_count += 1
                        
                    except Exception as e:
                        logger.error(f"Failed to sync collection: {e}")
                        continue
                
                logger.info(f"Synced {collections_count} collections to database")
            
            # Commit transaction
            self.db.commit()
            logger.info(f"Project {self.project_id} data sync complete")
            
        except Exception as e:
            logger.error(f"Failed to sync data to database: {e}")
            self.db.rollback()
    
    def _parse_time(self, time_str: str) -> float:
        """Parse time string to seconds"""
        try:
            if ',' in time_str:
                time_str = time_str.replace(',', '.')
            
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            else:
                return 0.0
        except:
            return 0.0

def create_pipeline_adapter(db: Session, task_id: str, project_id: str, progress_callback: Optional[Callable] = None) -> PipelineAdapter:
    """
    Create pipeline adapter instance
    
    Args:
        db: Database session
        task_id: Task ID
        project_id: Project ID
        progress_callback: Progress callback function
        
    Returns:
        Pipeline adapter instance
    """
    return PipelineAdapter(project_id, task_id, db, progress_callback)

def create_pipeline_adapter_sync(db: Session, task_id: str, project_id: str) -> PipelineAdapter:
    """
    Create pipeline adapter instance (sync version)
    
    Args:
        db: Database session
        task_id: Task ID
        project_id: Project ID
        
    Returns:
        Pipeline adapter instance
    """
    return PipelineAdapter(project_id, task_id, db)
