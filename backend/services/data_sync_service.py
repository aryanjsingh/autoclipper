"""
Data sync service - syncs processing results to database
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from backend.models.clip import Clip, ClipStatus
from backend.models.collection import Collection, CollectionStatus
from backend.models.project import Project, ProjectStatus, ProjectType
from backend.models.task import Task, TaskStatus, TaskType
from datetime import datetime

logger = logging.getLogger(__name__)


class DataSyncService:
    """Data sync service"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def sync_all_projects_from_filesystem(self, data_dir: Path) -> Dict[str, Any]:
        """Sync all projects from filesystem to database"""
        try:
            logger.info(f"Starting to sync all projects from filesystem: {data_dir}")
            
            projects_dir = data_dir / "projects"
            if not projects_dir.exists():
                logger.warning(f"Projects directory does not exist: {projects_dir}")
                return {"success": False, "error": "Projects directory does not exist"}
            
            synced_projects = []
            failed_projects = []
            
            # Iterate through all project directories
            for project_dir in projects_dir.iterdir():
                if project_dir.is_dir() and not project_dir.name.startswith('.'):
                    project_id = project_dir.name
                    try:
                        result = self.sync_project_from_filesystem(project_id, project_dir)
                        if result["success"]:
                            synced_projects.append(project_id)
                        else:
                            failed_projects.append({"project_id": project_id, "error": result.get("error")})
                    except Exception as e:
                        logger.error(f"Failed to sync project {project_id}: {str(e)}")
                        failed_projects.append({"project_id": project_id, "error": str(e)})
            
            logger.info(f"Sync completed: {len(synced_projects)} succeeded, {len(failed_projects)} failed")
            
            return {
                "success": True,
                "synced_projects": synced_projects,
                "failed_projects": failed_projects,
                "total_synced": len(synced_projects),
                "total_failed": len(failed_projects)
            }
            
        except Exception as e:
            logger.error(f"Failed to sync all projects: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def sync_project_from_filesystem(self, project_id: str, project_dir: Path) -> Dict[str, Any]:
        """Sync a single project from filesystem to database"""
        try:
            logger.info(f"Starting to sync project: {project_id}")
            
            # Check if project already exists in database
            existing_project = self.db.query(Project).filter(Project.id == project_id).first()
            if existing_project:
                logger.info(f"Project {project_id} already exists in database, continuing to sync clip data")
            else:
                # Read project metadata
                project_metadata = self._read_project_metadata(project_dir)
                if not project_metadata:
                    logger.warning(f"Project {project_id} has no metadata file, creating basic project record")
                    project_metadata = {
                        "project_name": f"Project_{project_id[:8]}",
                        "created_at": datetime.now().isoformat(),
                        "status": "pending"
                    }
                
                # Create project record
                project = Project(
                    id=project_id,
                    name=project_metadata.get("project_name", f"Project_{project_id[:8]}"),
                    description=project_metadata.get("description", ""),
                    project_type=ProjectType.KNOWLEDGE,  # Default type
                    status=ProjectStatus.PENDING,
                    processing_config=project_metadata.get("processing_config", {}),
                    project_metadata=project_metadata
                )
                
                self.db.add(project)
                self.db.commit()
                self.db.refresh(project)
                
                logger.info(f"Project {project_id} synced to database successfully")
            

            
            # Sync clip data
            clips_count = self._sync_clips_from_filesystem(project_id, project_dir)
            
            # Sync collection data
            logger.info(f"Starting to sync collection data for project {project_id}")
            collections_count = self._sync_collections_from_filesystem(project_id, project_dir)
            logger.info(f"Project {project_id} collection sync completed, synced {collections_count} collections")
            
            # Check if project processing is complete, update project status
            self._update_project_status_if_completed(project_id, project_dir)
            
            return {
                "success": True,
                "project_id": project_id,
                "clips_synced": clips_count,
                "collections_synced": collections_count
            }
            
        except Exception as e:
            logger.error(f"Failed to sync project {project_id}: {str(e)}")
            self.db.rollback()
            return {"success": False, "error": str(e)}
    
    def _read_project_metadata(self, project_dir: Path) -> Optional[Dict[str, Any]]:
        """Read project metadata"""
        metadata_files = [
            project_dir / "project.json",
            project_dir / "metadata.json",
            project_dir / "info.json"
        ]
        
        for metadata_file in metadata_files:
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logger.warning(f"Failed to read metadata file {metadata_file}: {e}")
        
        return None
    
    def _sync_clips_from_filesystem(self, project_id: str, project_dir: Path) -> int:
        """Sync clip data from filesystem"""
        try:
            # Find clip data files
            clips_files = [
                project_dir / "step6_video" / "clips_metadata.json",  # Most complete data source
                project_dir / "step3_all_scored.json",  # Prefer correct data source
                project_dir / "step4_title" / "step4_title.json",
                project_dir / "step4_titles.json",
                project_dir / "clips_metadata.json",
                project_dir / "metadata" / "clips_metadata.json"
            ]
            
            clips_data = None
            for clips_file in clips_files:
                logger.info(f"Checking clip file: {clips_file}")
                if clips_file.exists():
                    try:
                        with open(clips_file, 'r', encoding='utf-8') as f:
                            clips_data = json.load(f)
                        logger.info(f"Successfully read clip file: {clips_file}, data length: {len(clips_data) if isinstance(clips_data, list) else 'not list'}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to read clip file {clips_file}: {e}")
                else:
                    logger.info(f"Clip file does not exist: {clips_file}")
            
            if not clips_data:
                logger.info(f"No clip data found for project {project_id}")
                return 0
            
            # Ensure clips_data is a list
            if isinstance(clips_data, dict) and "clips" in clips_data:
                clips_data = clips_data["clips"]
            elif not isinstance(clips_data, list):
                logger.warning(f"Clip data format is incorrect for project {project_id}")
                return 0
            
            synced_count = 0
            updated_count = 0
            for clip_data in clips_data:
                try:
                    # Check if clip already exists
                    existing_clip = self.db.query(Clip).filter(
                        Clip.project_id == project_id,
                        Clip.title == clip_data.get("generated_title", clip_data.get("title", ""))
                    ).first()
                    
                    if existing_clip:
                        # Update existing clip's video_path and tags, force use project internal output directory
                        clip_id = clip_data.get('id', str(synced_count + 1))
                        safe_title = clip_data.get('generated_title', clip_data.get('title', clip_data.get('outline', '')))
                        # Clean filename, remove special characters
                        safe_title = "".join(c for c in safe_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_title = safe_title.replace(' ', '_')
                        
                        # Force use project internal standard path
                        from ..core.path_utils import get_project_directory
                        project_dir = get_project_directory(project_id)
                        project_clips_dir = project_dir / "output" / "clips"
                        project_clips_dir.mkdir(parents=True, exist_ok=True)
                        project_video_path = project_clips_dir / f"{clip_id}_{safe_title}.mp4"
                        
                        # Compatible with old global output directory, migrate if exists
                        from ..core.path_utils import get_data_directory
                        legacy_video_path = get_data_directory() / "output" / "clips" / f"{clip_id}_{safe_title}.mp4"
                        try:
                            if legacy_video_path.exists() and not project_video_path.exists():
                                import shutil
                                shutil.copy2(legacy_video_path, project_video_path)
                                logger.info(f"Migrated old clip file to project directory: {legacy_video_path} -> {project_video_path}")
                        except Exception as _e:
                            logger.warning(f"Failed to migrate old clip file: {legacy_video_path} -> {project_video_path}: {_e}")
                        
                        # Always use project internal path
                        video_path = str(project_video_path)
                        logger.info(f"Updating clip {existing_clip.id} video_path: {video_path}")
                        existing_clip.video_path = video_path
                        if existing_clip.tags is None:
                            existing_clip.tags = []  # Ensure tags is an empty list instead of null
                        updated_count += 1
                        continue
                    
                    # Convert time format
                    start_time = self._convert_time_to_seconds(clip_data.get('start_time', '00:00:00'))
                    end_time = self._convert_time_to_seconds(clip_data.get('end_time', '00:00:00'))
                    duration = end_time - start_time
                    
                    # Build video file path, force use project internal directory
                    clip_id = clip_data.get('id', str(synced_count + 1))
                    title = clip_data.get('generated_title', clip_data.get('title', clip_data.get('outline', '')))
                    
                    # Force use project internal path
                    from ..core.path_utils import get_project_directory, get_data_directory
                    project_dir = get_project_directory(project_id)
                    project_clips_dir = project_dir / "output" / "clips"
                    project_clips_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Find actual filename (preserve special characters)
                    actual_filename = None
                    for file_path in project_clips_dir.glob(f"{clip_id}_*.mp4"):
                        actual_filename = file_path.name
                        break
                    
                    if actual_filename:
                        project_video_path = project_clips_dir / actual_filename
                    else:
                        # If actual file not found, use cleaned filename as fallback
                        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_title = safe_title.replace(' ', '_')
                        project_video_path = project_clips_dir / f"{clip_id}_{safe_title}.mp4"
                    
                    # Compatible with old global output directory, migrate if exists
                    global_clips_dir = get_data_directory() / "output" / "clips"
                    if actual_filename:
                        global_video_path = global_clips_dir / actual_filename
                    else:
                        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
                        safe_title = safe_title.replace(' ', '_')
                        global_video_path = global_clips_dir / f"{clip_id}_{safe_title}.mp4"
                    
                    if global_video_path.exists() and not project_video_path.exists():
                        import shutil
                        shutil.copy2(global_video_path, project_video_path)
                        logger.info(f"Migrated clip file from global directory to project directory: {global_video_path} -> {project_video_path}")
                    
                    # Always use project internal path
                    video_path = str(project_video_path)
                    
                    # Create clip record
                    clip = Clip(
                        project_id=project_id,
                        title=clip_data.get('generated_title', clip_data.get('title', clip_data.get('outline', ''))),
                        description=clip_data.get('recommend_reason', ''),
                        start_time=start_time,
                        end_time=end_time,
                        duration=duration,
                        score=clip_data.get('final_score', 0.0),
                        video_path=video_path,
                        tags=[],  # Ensure tags is an empty list instead of null
                        clip_metadata=clip_data,
                        status=ClipStatus.COMPLETED
                    )
                    
                    self.db.add(clip)
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync clip: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"Project {project_id} synced {synced_count} clips, updated {updated_count} clips")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync clip data: {str(e)}")
            return 0
    
    def _sync_collections_from_filesystem(self, project_id: str, project_dir: Path) -> int:
        """Sync collection data from filesystem"""
        try:
            # Find collection data files
            collections_files = [
                project_dir / "step6_video" / "collections_metadata.json",  # Most complete data source
                project_dir / "step5_clustering" / "step5_clustering.json",
                project_dir / "metadata" / "step5_collections.json",  # Added step5_collections.json
                project_dir / "collections_metadata.json",
                project_dir / "metadata" / "collections_metadata.json"
            ]
            
            collections_data = None
            for collections_file in collections_files:
                logger.info(f"Checking collection file: {collections_file}")
                if collections_file.exists():
                    try:
                        with open(collections_file, 'r', encoding='utf-8') as f:
                            collections_data = json.load(f)
                        logger.info(f"Successfully read collection file: {collections_file}, data length: {len(collections_data) if isinstance(collections_data, list) else 'not list'}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to read collection file {collections_file}: {e}")
                else:
                    logger.info(f"Collection file does not exist: {collections_file}")
            
            if not collections_data:
                logger.info(f"No collection data found for project {project_id}")
                return 0
            
            # Ensure collections_data is a list
            if isinstance(collections_data, dict) and "collections" in collections_data:
                collections_data = collections_data["collections"]
            elif not isinstance(collections_data, list):
                logger.warning(f"Collection data format is incorrect for project {project_id}")
                return 0
            
            # Read deletion record file
            deleted_collections_file = project_dir / "deleted_collections.json"
            deleted_collections = set()
            if deleted_collections_file.exists():
                try:
                    with open(deleted_collections_file, 'r', encoding='utf-8') as f:
                        deleted_data = json.load(f)
                        deleted_collections = set(deleted_data.get('deleted_collection_ids', []))
                except Exception as e:
                    logger.warning(f"Failed to read deletion records: {e}")
            
            synced_count = 0
            for collection_data in collections_data:
                try:
                    collection_id = collection_data.get("id", "")
                    collection_title = collection_data.get("collection_title", "")
                    
                    # Check if it has been deleted
                    if collection_id in deleted_collections:
                        logger.info(f"Collection {collection_id} has been deleted, skipping sync")
                        continue
                    
                    # Check if collection already exists
                    existing_collection = self.db.query(Collection).filter(
                        Collection.project_id == project_id,
                        Collection.name == collection_title
                    ).first()
                    
                    if existing_collection:
                        # Collection already exists, check if association relationship needs to be established
                        collection = existing_collection
                        logger.info(f"Collection {collection_title} already exists, checking associations")
                    else:
                        # Create new collection
                        collection = None
                    
                    # Build collection video file path, force use project internal directory
                    # Try multiple possible filename formats
                    possible_filenames = [
                        f"{collection_id}_{collection_title}.mp4",
                        f"{collection_title}.mp4",
                        f"collection_{collection_id}.mp4"
                    ]
                    
                    from ..core.path_utils import get_project_directory, get_data_directory
                    project_dir = get_project_directory(project_id)
                    project_collections_dir = project_dir / "output" / "collections"
                    project_collections_dir.mkdir(parents=True, exist_ok=True)
                    
                    video_path = None
                    # First look in project directory
                    for filename in possible_filenames:
                        project_video_path = project_collections_dir / filename
                        if project_video_path.exists():
                            video_path = str(project_video_path)
                            break
                    
                    # If not found in project directory, try global directory and migrate
                    if not video_path:
                        for filename in possible_filenames:
                            legacy_video_path = get_data_directory() / "output" / "collections" / filename
                            if legacy_video_path.exists():
                                # Migrate to project directory
                                project_video_path = project_collections_dir / filename
                                import shutil
                                shutil.copy2(legacy_video_path, project_video_path)
                                video_path = str(project_video_path)
                                logger.info(f"Migrated collection file from global directory to project directory: {legacy_video_path} -> {project_video_path}")
                                break
                    
                    # If still not found, use project internal path (file may not have been generated yet)
                    if not video_path:
                        video_path = str(project_collections_dir / possible_filenames[0])
                    
                    # Convert numeric clip_ids to UUID format
                    original_clip_ids = collection_data.get('clip_ids', [])
                    uuid_clip_ids = []
                    
                    # Get mapping of all clips in the project (numeric ID -> UUID)
                    clips = self.db.query(Clip).filter(Clip.project_id == project_id).all()
                    clip_id_mapping = {}
                    for clip in clips:
                        # Get original ID from clip_metadata
                        if clip.clip_metadata and 'id' in clip.clip_metadata:
                            original_id = str(clip.clip_metadata['id'])
                            clip_id_mapping[original_id] = clip.id
                    
                    # Convert clip_ids
                    for original_id in original_clip_ids:
                        if str(original_id) in clip_id_mapping:
                            uuid_clip_ids.append(clip_id_mapping[str(original_id)])
                        else:
                            logger.warning(f"Cannot find UUID for clip ID {original_id}")
                    
                    # If collection does not exist, create new collection
                    if not collection:
                        collection = Collection(
                            project_id=project_id,
                            name=collection_title,
                            description=collection_data.get('collection_summary', ''),
                            video_path=video_path,
                            export_path=video_path,  # Set export_path
                            collection_metadata={
                                'clip_ids': uuid_clip_ids,  # Use UUID format clip_ids
                                'original_clip_ids': original_clip_ids,  # Keep original numeric IDs
                                'collection_type': 'ai_recommended',
                                'original_id': collection_id
                            },
                            status=CollectionStatus.COMPLETED
                        )
                        
                        self.db.add(collection)
                        self.db.flush()  # Ensure collection has an ID
                        logger.info(f"Created new collection: {collection.id}")
                    else:
                        # Update existing collection metadata
                        if not collection.collection_metadata:
                            collection.collection_metadata = {}
                        collection.collection_metadata.update({
                            'clip_ids': uuid_clip_ids,
                            'original_clip_ids': original_clip_ids,
                            'collection_type': 'ai_recommended',
                            'original_id': collection_id
                        })
                        collection.video_path = video_path
                        collection.export_path = video_path  # Set export_path
                        logger.info(f"Updated existing collection: {collection.id}")
                    
                    # Establish association between collection and clips
                    for i, clip_id in enumerate(uuid_clip_ids):
                        try:
                            # Check if clip exists
                            clip = self.db.query(Clip).filter(Clip.id == clip_id).first()
                            if clip:
                                # Check if association already exists
                                from ..models.collection import clip_collection
                                existing_relation = self.db.execute(
                                    clip_collection.select().where(
                                        clip_collection.c.clip_id == clip_id,
                                        clip_collection.c.collection_id == collection.id
                                    )
                                ).first()
                                
                                if not existing_relation:
                                    # Insert record using association table
                                    stmt = clip_collection.insert().values(
                                        clip_id=clip_id,
                                        collection_id=collection.id,
                                        order_index=i
                                    )
                                    self.db.execute(stmt)
                                    logger.info(f"Established association between collection {collection.id} and clip {clip_id}")
                                else:
                                    logger.info(f"Association between collection {collection.id} and clip {clip_id} already exists")
                            else:
                                logger.warning(f"Clip {clip_id} does not exist, skipping association")
                        except Exception as e:
                            logger.error(f"Failed to establish collection-clip association: {e}")
                    
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to sync collection: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"Project {project_id} synced {synced_count} collections")
            return synced_count
            
        except Exception as e:
            logger.error(f"Failed to sync collection data: {str(e)}")
            return 0
    
    def sync_project_data(self, project_id: str, project_dir: Path) -> Dict[str, Any]:
        """Sync project data to database"""
        try:
            logger.info(f"Starting to sync project data: {project_id}")
            
            # Sync clips data
            clips_count = self._sync_clips(project_id, project_dir)
            
            # Sync collections data
            collections_count = self._sync_collections(project_id, project_dir)
            
            # Update project statistics
            self._update_project_stats(project_id, clips_count, collections_count)
            
            logger.info(f"Project data sync complete: {project_id}, clips: {clips_count}, collections: {collections_count}")
            
            return {
                "success": True,
                "clips_synced": clips_count,
                "collections_synced": collections_count
            }
            
        except Exception as e:
            logger.error(f"Failed to sync project data: {str(e)}")
            raise
    
    def _sync_clips(self, project_id: str, project_dir: Path) -> int:
        """Sync clips data"""
        clips_file = project_dir / "step4_titles.json"
        if not clips_file.exists():
            logger.warning(f"Clips file does not exist: {clips_file}")
            return 0
        
        try:
            with open(clips_file, 'r', encoding='utf-8') as f:
                clips_data = json.load(f)
            
            clips_count = 0
            for clip_data in clips_data:
                # Check if already exists
                existing_clip = self.db.query(Clip).filter(
                    Clip.project_id == project_id,
                    Clip.title == clip_data.get("generated_title")
                ).first()
                
                if existing_clip:
                    logger.info(f"Clip already exists, skipping: {clip_data.get('generated_title')}")
                    continue
                
                # Create new clip record
                clip = Clip(
                    project_id=project_id,
                    title=clip_data.get("generated_title", ""),
                    description=clip_data.get("outline", ""),
                    start_time=self._parse_time(clip_data.get("start_time", "00:00:00")),
                    end_time=self._parse_time(clip_data.get("end_time", "00:00:00")),
                    duration=self._calculate_duration(
                        clip_data.get("start_time", "00:00:00"),
                        clip_data.get("end_time", "00:00:00")
                    ),
                    score=clip_data.get("final_score", 0.0),
                    status=ClipStatus.COMPLETED,
                    tags=[],
                    clip_metadata={
                        "outline": clip_data.get("outline"),
                        "content": clip_data.get("content", []),
                        "recommend_reason": clip_data.get("recommend_reason"),
                        "chunk_index": clip_data.get("chunk_index"),
                        "original_id": clip_data.get("id")
                    }
                )
                
                self.db.add(clip)
                clips_count += 1
                logger.info(f"Created clip: {clip.title}")
            
            self.db.commit()
            logger.info(f"Synced {clips_count} clips")
            return clips_count
            
        except Exception as e:
            logger.error(f"Failed to sync clips: {str(e)}")
            self.db.rollback()
            raise
    
    def _sync_collections(self, project_id: str, project_dir: Path) -> int:
        """Sync collections data to database"""
        collections_file = project_dir / "step5_collections.json"
        if not collections_file.exists():
            logger.warning(f"Collections file does not exist: {collections_file}")
            return 0
        
        try:
            with open(collections_file, 'r', encoding='utf-8') as f:
                collections_data = json.load(f)
            
            collections_count = 0
            for collection_data in collections_data:
                # Check if already exists
                existing_collection = self.db.query(Collection).filter(
                    Collection.project_id == project_id,
                    Collection.name == collection_data.get("collection_title")
                ).first()
                
                if existing_collection:
                    logger.info(f"Collection already exists, skipping: {collection_data.get('collection_title')}")
                    continue
                
                # Create new collection record
                collection = Collection(
                    project_id=project_id,
                    name=collection_data.get("collection_title", ""),
                    description=collection_data.get("collection_summary", ""),
                    theme="default",
                    status=CollectionStatus.COMPLETED,
                    tags=[],
                    collection_metadata={
                        "clip_ids": collection_data.get("clip_ids", []),
                        "original_id": collection_data.get("id"),
                        "collection_type": "ai_recommended"  # Mark as AI recommended
                    }
                )
                
                self.db.add(collection)
                collections_count += 1
                logger.info(f"Created collection: {collection.name}")
            
            self.db.commit()
            logger.info(f"Synced {collections_count} collections")
            return collections_count
            
        except Exception as e:
            logger.error(f"Failed to sync collections: {str(e)}")
            self.db.rollback()
            raise
    
    def _update_project_stats(self, project_id: str, clips_count: int, collections_count: int):
        """Update project statistics"""
        try:
            project = self.db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.total_clips = clips_count
                project.total_collections = collections_count
                self.db.commit()
                logger.info(f"Updated project stats: clips={clips_count}, collections={collections_count}")
        except Exception as e:
            logger.error(f"Failed to update project stats: {str(e)}")
    
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
        except Exception:
            return 0.0
    
    def _calculate_duration(self, start_time: str, end_time: str) -> float:
        """Calculate duration"""
        start_seconds = self._parse_time(start_time)
        end_seconds = self._parse_time(end_time)
        return end_seconds - start_seconds

    def _convert_time_to_seconds(self, time_str: str) -> int:
        """Convert time string to seconds"""
        try:
            # Handle format "00:00:00,120" or "00:00:00.120"
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds_parts = parts[2].split('.')
            seconds = int(seconds_parts[0])
            milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
            return int(total_seconds)
        except Exception as e:
            logger.error(f"Time conversion failed: {time_str}, error: {e}")
            return 0
    
    def _update_project_status_if_completed(self, project_id: str, project_dir: Path):
        """Check if project processing is complete, if so update status to completed"""
        try:
            # Check if step6_video_output.json file exists, this is the indicator of processing completion
            step6_output_file = project_dir / "output" / "step6_video_output.json"
            
            if step6_output_file.exists():
                # Get project record
                project = self.db.query(Project).filter(Project.id == project_id).first()
                if project and project.status != ProjectStatus.COMPLETED:
                    # Read step6 output file to get statistics
                    try:
                        with open(step6_output_file, 'r', encoding='utf-8') as f:
                            step6_output = json.load(f)
                        
                        # Update project status and statistics
                        project.status = ProjectStatus.COMPLETED
                        project.total_clips = step6_output.get("clips_count", 0)
                        project.total_collections = step6_output.get("collections_count", 0)
                        project.completed_at = datetime.now()
                        
                        self.db.commit()
                        logger.info(f"Project {project_id} status updated to completed, clips: {project.total_clips}, collections: {project.total_collections}")
                        
                    except Exception as e:
                        logger.error(f"Failed to read step6 output file: {e}")
                        # Even if reading fails, mark as completed
                        project.status = ProjectStatus.COMPLETED
                        project.completed_at = datetime.now()
                        self.db.commit()
                        logger.info(f"Project {project_id} status updated to completed (no statistics)")
                        
        except Exception as e:
            logger.error(f"Failed to update project status: {e}")
