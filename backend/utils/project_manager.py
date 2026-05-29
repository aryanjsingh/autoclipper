"""
Project management utility
"""
import json
import logging
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Fix import issues
try:
    from ..core.shared_config import config_manager
except ImportError:
    # If relative import fails, try absolute import
    import sys
    from pathlib import Path
    backend_path = Path(__file__).parent.parent
    if str(backend_path) not in sys.path:
        sys.path.insert(0, str(backend_path))
    from ..core.shared_config import config_manager

logger = logging.getLogger(__name__)

class ProjectManager:
    """Project data manager"""
    
    def __init__(self):
        self.config = config_manager
    
    def create_project(self, project_name: Optional[str] = None) -> str:
        """
        Create new project
        
        Args:
            project_name: Project name (optional)
            
        Returns:
            Project ID
        """
        project_id = str(uuid.uuid4())
        project_name = project_name or f"project_{project_id[:8]}"
        
        # Ensure project directory structure exists
        self.config.ensure_project_directories(project_id)
        
        # Create project metadata
        project_metadata = {
            "project_id": project_id,
            "project_name": project_name,
            "created_at": datetime.now().isoformat(),
            "status": "created",
            "current_step": 0,
            "total_steps": 6,
            "error_message": None,
            "file_info": {
                "video_file": None,
                "srt_file": None,
                "txt_file": None
            }
        }
        
        # Save project metadata
        self._save_project_metadata(project_id, project_metadata)
        
        logger.info(f"Created project: {project_id} ({project_name})")
        return project_id
    
    def get_project_paths(self, project_id: str) -> Dict[str, Path]:
        """
        Get project path configuration
        
        Args:
            project_id: Project ID
            
        Returns:
            Project path dictionary
        """
        return self.config.get_project_paths(project_id)
    
    def validate_project_exists(self, project_id: str) -> bool:
        """
        Validate if project exists
        
        Args:
            project_id: Project ID
            
        Returns:
            Whether project exists
        """
        paths = self.get_project_paths(project_id)
        return paths["project_base"].exists()
    
    def get_project_metadata(self, project_id: str) -> Dict[str, Any]:
        """
        Get project metadata
        
        Args:
            project_id: Project ID
            
        Returns:
            Project metadata
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        metadata_file = self.get_project_paths(project_id)["metadata_dir"] / "project_metadata.json"
        
        if not metadata_file.exists():
            # If metadata file does not exist, create default metadata
            default_metadata = {
                "project_id": project_id,
                "project_name": f"project_{project_id[:8]}",
                "created_at": datetime.now().isoformat(),
                "status": "unknown",
                "current_step": 0,
                "total_steps": 6,
                "error_message": None,
                "file_info": {
                    "video_file": None,
                    "srt_file": None,
                    "txt_file": None
                }
            }
            self._save_project_metadata(project_id, default_metadata)
            return default_metadata
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise FileIOError(f"Failed to read project metadata: {e}")
    
    def update_project_metadata(self, project_id: str, updates: Dict[str, Any]):
        """
        Update project metadata
        
        Args:
            project_id: Project ID
            updates: Fields to update
        """
        metadata = self.get_project_metadata(project_id)
        metadata.update(updates)
        metadata["updated_at"] = datetime.now().isoformat()
        
        self._save_project_metadata(project_id, metadata)
    
    def _save_project_metadata(self, project_id: str, metadata: Dict[str, Any]) -> None:
        """Save project metadata"""
        paths = self.get_project_paths(project_id)
        metadata_dir = paths["metadata_dir"]
        metadata_file = metadata_dir / "project_metadata.json"
        
        try:
            # Ensure metadata directory exists
            metadata_dir.mkdir(parents=True, exist_ok=True)
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            raise FileIOError(f"Failed to save project metadata: {e}")
    
    def save_input_file(self, project_id: str, file_path: Path, file_type: str) -> str:
        """
        Save input file to project directory
        
        Args:
            project_id: Project ID
            file_path: Source file path
            file_type: File type (video, srt, txt)
            
        Returns:
            Saved file path
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        if not file_path.exists():
            raise FileIOError(f"Source file does not exist: {file_path}")
        
        paths = self.get_project_paths(project_id)
        input_dir = paths["input_dir"]
        
        # Determine target file name
        if file_type == "video":
            target_name = "input.mp4"
        elif file_type == "srt":
            target_name = "input.srt"
        elif file_type == "txt":
            target_name = "input.txt"
        else:
            raise ValidationError(f"Unsupported file type: {file_type}")
        
        target_path = input_dir / target_name
        
        try:
            # Copy file
            shutil.copy2(file_path, target_path)
            
            # Update project metadata
            metadata = self.get_project_metadata(project_id)
            metadata["file_info"][f"{file_type}_file"] = str(target_path)
            self._save_project_metadata(project_id, metadata)
            
            logger.info(f"File saved to project {project_id}: {target_path}")
            return str(target_path)
            
        except Exception as e:
            raise FileIOError(f"Failed to save file: {e}")
    
    def get_input_files(self, project_id: str) -> Dict[str, Optional[Path]]:
        """
        Get project input files
        
        Args:
            project_id: Project ID
            
        Returns:
            Input file path dictionary
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        paths = self.get_project_paths(project_id)
        project_base = paths["project_base"]
        input_dir = paths["input_dir"]
        
        # Check two possible locations: input subdirectory and project root
        file_names = ["input.mp4", "input.srt", "input.txt"]
        file_keys = ["video_file", "srt_file", "txt_file"]
        
        files = {}
        for key, name in zip(file_keys, file_names):
            # Prioritize checking input subdirectory
            input_path = input_dir / name
            if input_path.exists():
                files[key] = input_path
            else:
                # Check project root
                root_path = project_base / name
                if root_path.exists():
                    files[key] = root_path
                else:
                    files[key] = None
        
        return files
    
    def validate_input_files(self, project_id: str) -> Dict[str, bool]:
        """
        Validate project input files
        
        Args:
            project_id: Project ID
            
        Returns:
            File validation result
        """
        files = self.get_input_files(project_id)
        
        validation = {
            "has_video": files["video_file"] is not None,
            "has_srt": files["srt_file"] is not None,
            "has_txt": files["txt_file"] is not None,
            "can_process": files["video_file"] is not None and files["srt_file"] is not None
        }
        
        return validation
    
    def save_processing_result(self, project_id: str, step: int, result: Dict[str, Any]):
        """
        Save processing result
        
        Args:
            project_id: Project ID
            step: Processing step
            result: Processing result
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        paths = self.get_project_paths(project_id)
        metadata_dir = paths["metadata_dir"]
        
        # Ensure metadata directory exists
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Save step result
        step_file = metadata_dir / f"step{step}_result.json"
        
        try:
            with open(step_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            # Update project status
            self.update_project_metadata(project_id, {
                "current_step": step,
                "status": "processing" if step < 6 else "completed"
            })
            
            logger.info(f"Step {step} result saved to project {project_id}")
            
        except Exception as e:
            raise FileIOError(f"Failed to save processing result: {e}")
    
    def get_processing_result(self, project_id: str, step: int) -> Optional[Dict[str, Any]]:
        """
        Get processing result
        
        Args:
            project_id: Project ID
            step: Processing step
            
        Returns:
            Processing result, returns None if not found
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        paths = self.get_project_paths(project_id)
        metadata_dir = paths["metadata_dir"]
        step_file = metadata_dir / f"step{step}_result.json"
        
        if not step_file.exists():
            return None
        
        try:
            with open(step_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise FileIOError(f"Failed to read processing result: {e}")
    
    def save_clip(self, project_id: str, clip_data: Dict[str, Any], clip_index: int):
        """
        Save video clip information
        
        Args:
            project_id: Project ID
            clip_data: Clip data
            clip_index: Clip index
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        paths = self.get_project_paths(project_id)
        metadata_dir = paths["metadata_dir"]
        
        # Ensure metadata directory exists
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Read existing clip data
        clips_file = metadata_dir / "clips_metadata.json"
        clips_data = []
        
        if clips_file.exists():
            try:
                with open(clips_file, 'r', encoding='utf-8') as f:
                    clips_data = json.load(f)
            except Exception:
                clips_data = []
        
        # Add new clip
        clip_data["clip_index"] = clip_index
        clip_data["created_at"] = datetime.now().isoformat()
        
        # Ensure no duplicate additions
        existing_indices = [clip["clip_index"] for clip in clips_data]
        if clip_index in existing_indices:
            # Update existing clip
            for i, clip in enumerate(clips_data):
                if clip["clip_index"] == clip_index:
                    clips_data[i] = clip_data
                    break
        else:
            # Add new clip
            clips_data.append(clip_data)
        
        # Save clip data
        try:
            with open(clips_file, 'w', encoding='utf-8') as f:
                json.dump(clips_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Clip {clip_index} saved to project {project_id}")
            
        except Exception as e:
            raise FileIOError(f"Failed to save clip data: {e}")
    
    def get_clips(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all clips of a project
        
        Args:
            project_id: Project ID
            
        Returns:
            List of clips
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        paths = self.get_project_paths(project_id)
        metadata_dir = paths["metadata_dir"]
        clips_file = metadata_dir / "clips_metadata.json"
        
        if not clips_file.exists():
            return []
        
        try:
            with open(clips_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise FileIOError(f"Failed to read clip data: {e}")
    
    def save_collection(self, project_id: str, collection_data: Dict[str, Any]):
        """
        Save collection information
        
        Args:
            project_id: Project ID
            collection_data: Collection data
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        paths = self.get_project_paths(project_id)
        metadata_dir = paths["metadata_dir"]
        
        # Ensure metadata directory exists
        metadata_dir.mkdir(parents=True, exist_ok=True)
        
        # Read existing collection data
        collections_file = metadata_dir / "collections_metadata.json"
        collections_data = []
        
        if collections_file.exists():
            try:
                with open(collections_file, 'r', encoding='utf-8') as f:
                    collections_data = json.load(f)
            except Exception:
                collections_data = []
        
        # Add new collection
        collection_data["created_at"] = datetime.now().isoformat()
        collections_data.append(collection_data)
        
        # Save collection data
        try:
            with open(collections_file, 'w', encoding='utf-8') as f:
                json.dump(collections_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Collection saved to project {project_id}")
            
        except Exception as e:
            raise FileIOError(f"Failed to save collection data: {e}")
    
    def get_collections(self, project_id: str) -> List[Dict[str, Any]]:
        """
        Get all collections of a project
        
        Args:
            project_id: Project ID
            
        Returns:
            List of collections
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        paths = self.get_project_paths(project_id)
        metadata_dir = paths["metadata_dir"]
        collections_file = metadata_dir / "collections_metadata.json"
        
        if not collections_file.exists():
            return []
        
        try:
            with open(collections_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise FileIOError(f"Failed to read collection data: {e}")
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """
        List all projects
        
        Returns:
            List of projects
        """
        projects = []
        uploads_dir = Path(self.config.settings.uploads_dir)
        
        if not uploads_dir.exists():
            return projects
        
        for project_dir in uploads_dir.iterdir():
            if project_dir.is_dir() and not project_dir.name.startswith('.'):
                try:
                    metadata = self.get_project_metadata(project_dir.name)
                    projects.append(metadata)
                except Exception as e:
                    logger.warning(f"Failed to read project {project_dir.name} metadata: {e}")
        
        # Sort by creation time
        projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return projects
    
    def delete_project(self, project_id: str) -> bool:
        """
        Delete project
        
        Args:
            project_id: Project ID
            
        Returns:
            Whether deletion was successful
        """
        if not self.validate_project_exists(project_id):
            logger.warning(f"Project does not exist: {project_id}")
            return False
        
        paths = self.get_project_paths(project_id)
        project_base = paths["project_base"]
        
        try:
            shutil.rmtree(project_base)
            logger.info(f"Project deleted: {project_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete project: {e}")
            return False
    
    def get_project_summary(self, project_id: str) -> Dict[str, Any]:
        """
        Get project summary information
        
        Args:
            project_id: Project ID
            
        Returns:
            Project summary
        """
        if not self.validate_project_exists(project_id):
            raise FileIOError(f"Project does not exist: {project_id}")
        
        metadata = self.get_project_metadata(project_id)
        validation = self.validate_input_files(project_id)
        clips = self.get_clips(project_id)
        collections = self.get_collections(project_id)
        
        return {
            "project_info": metadata,
            "file_validation": validation,
            "clips_count": len(clips),
            "collections_count": len(collections),
            "processing_progress": {
                "current_step": metadata.get("current_step", 0),
                "total_steps": metadata.get("total_steps", 6),
                "progress_percentage": (metadata.get("current_step", 0) / metadata.get("total_steps", 6)) * 100
            }
        }

# Global project manager instance
project_manager = ProjectManager()
