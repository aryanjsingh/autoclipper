#!/usr/bin/env python3
"""
Script to execute the real pipeline using the original architecture
Uses PipelineAdapter and the original pipeline steps
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ..core.database import SessionLocal
from ..models.project import Project, ProjectStatus
from ..models.task import Task, TaskStatus
from ..services.pipeline_adapter import create_pipeline_adapter_sync
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def execute_real_pipeline(project_id: str):
    """Execute the real pipeline using the original architecture"""
    
    logger.info(f"Starting real pipeline execution for project {project_id}")
    
    try:
        # Create database session
        db = SessionLocal()
        
        try:
            # Verify project exists
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                raise ValueError(f"Project {project_id} does not exist")
            
            logger.info(f"Verified project exists: {project.name}")
            
            # Create task record
            task = Task(
                name=f"Real pipeline processing",
                description=f"Processing project {project_id} using original architecture",
                task_type="VIDEO_PROCESSING",
                project_id=project_id,
                status=TaskStatus.RUNNING,
                progress=0,
                current_step="Initializing",
                total_steps=6
            )
            db.add(task)
            db.commit()
            db.refresh(task)
            
            logger.info(f"Task record created: {task.id}")
            
            # Prepare file paths
            data_root = project_root / "data" / "projects" / project_id
            input_video_path = data_root / "raw" / "input.mp4"
            input_srt_path = data_root / "raw" / "input.srt"
            
            # Verify files exist
            if not input_video_path.exists():
                raise FileNotFoundError(f"Video file not found: {input_video_path}")
            if not input_srt_path.exists():
                raise FileNotFoundError(f"Subtitle file not found: {input_srt_path}")
            
            logger.info(f"File paths verified:")
            logger.info(f"  Video: {input_video_path}")
            logger.info(f"  Subtitles: {input_srt_path}")
            
            # Create pipeline adapter
            pipeline_adapter = create_pipeline_adapter_sync(db, str(task.id), project_id)
            
            # Validate pipeline prerequisites
            logger.info("Validating pipeline prerequisites...")
            errors = pipeline_adapter.validate_pipeline_prerequisites()
            if errors:
                error_msg = "; ".join(errors)
                logger.error(f"Pipeline prerequisite validation failed: {error_msg}")
                raise ValueError(f"Pipeline prerequisite validation failed: {error_msg}")
            
            logger.info("Pipeline prerequisites validated")
            
            # Execute full pipeline processing
            logger.info("Starting full pipeline execution...")
            result = pipeline_adapter.process_project_sync(
                project_id=project_id,
                input_video_path=str(input_video_path),
                input_srt_path=str(input_srt_path)
            )
            
            # Check processing result
            if result.get('status') == 'failed':
                error_msg = result.get('message', 'Processing failed')
                logger.error(f"Pipeline processing failed: {error_msg}")
                
                # Update task status to failed
                task.status = TaskStatus.FAILED
                task.error_message = error_msg
                db.commit()
                
                return {
                    "success": False,
                    "error": error_msg,
                    "result": result
                }
            else:
                # Processing succeeded
                logger.info("🎉 Pipeline processing succeeded!")
                logger.info(f"Processing result: {result}")
                
                # Update task status to completed
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.current_step = "Processing complete"
                db.commit()
                
                return {
                    "success": True,
                    "result": result,
                    "message": "Pipeline processing complete"
                }
                
        finally:
            db.close()
            
    except Exception as e:
        error_msg = f"Pipeline execution failed: {str(e)}"
        logger.error(error_msg)
        
        # Try to update task status
        try:
            db = SessionLocal()
            task = db.query(Task).filter(Task.project_id == project_id).order_by(Task.created_at.desc()).first()
            if task:
                task.status = TaskStatus.FAILED
                task.error_message = error_msg
                db.commit()
            db.close()
        except Exception as db_error:
            logger.error(f"Failed to update task status: {db_error}")
        
        return {
            "success": False,
            "error": error_msg
        }

async def main():
    """Main entry point"""
    if len(sys.argv) != 2:
        print("Usage: python execute_real_pipeline.py <project_id>")
        sys.exit(1)
    
    project_id = sys.argv[1]
    
    result = await execute_real_pipeline(project_id)
    
    if result["success"]:
        print(f"✅ Pipeline execution succeeded!")
        print(f"📊 Result: {result['result']}")
    else:
        print(f"❌ Pipeline execution failed: {result['error']}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
