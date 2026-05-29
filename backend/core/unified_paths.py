"""
Unified Path Configuration Management
Ensures all path configurations are obtained from a single source, avoiding path confusion
"""

from pathlib import Path
from typing import Dict, Any

class UnifiedPathManager:
    """Unified path manager"""
    
    def __init__(self):
        self._project_root = self._get_project_root()
        self._data_dir = self._project_root / "data"
        self._output_dir = self._data_dir / "output"
        
        # Ensure critical directories exist
        self._ensure_directories()
    
    def _get_project_root(self) -> Path:
        """Get project root directory"""
        current_path = Path(__file__).parent  # backend/core/

        # Search upward for project root directory
        while current_path.parent != current_path:
            if (current_path.parent / "backend").exists():
                return current_path.parent
            current_path = current_path.parent

        # If not found, use default path
        return Path(__file__).parent.parent.parent
    
    def _ensure_directories(self):
        """Ensure critical directories exist"""
        directories = [
            self._data_dir,
            self._output_dir,
            self._output_dir / "clips",
            self._output_dir / "collections",
            self._output_dir / "metadata",
            self._data_dir / "projects",
            self._data_dir / "uploads",
            self._data_dir / "temp",
            self._data_dir / "backups"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def project_root(self) -> Path:
        """Project root directory"""
        return self._project_root
    
    @property
    def data_directory(self) -> Path:
        """Data directory"""
        return self._data_dir
    
    @property
    def output_directory(self) -> Path:
        """Output directory"""
        return self._output_dir
    
    @property
    def clips_directory(self) -> Path:
        """Clips directory"""
        return self._output_dir / "clips"
    
    @property
    def collections_directory(self) -> Path:
        """Collections directory"""
        return self._output_dir / "collections"
    
    @property
    def metadata_directory(self) -> Path:
        """Metadata directory"""
        return self._output_dir / "metadata"
    
    @property
    def projects_directory(self) -> Path:
        """Projects directory"""
        return self._data_dir / "projects"
    
    @property
    def uploads_directory(self) -> Path:
        """Uploads directory"""
        return self._data_dir / "uploads"
    
    @property
    def temp_directory(self) -> Path:
        """Temporary directory"""
        return self._data_dir / "temp"
    
    @property
    def backups_directory(self) -> Path:
        """Backups directory"""
        return self._data_dir / "backups"
    
    def get_project_directory(self, project_id: str) -> Path:
        """Get project directory"""
        project_dir = self.projects_directory / project_id
        project_dir.mkdir(exist_ok=True)
        return project_dir
    
    def get_project_raw_directory(self, project_id: str) -> Path:
        """Get project raw files directory"""
        raw_dir = self.get_project_directory(project_id) / "raw"
        raw_dir.mkdir(exist_ok=True)
        return raw_dir
    
    def get_project_output_directory(self, project_id: str) -> Path:
        """Get project output directory"""
        output_dir = self.get_project_directory(project_id) / "output"
        output_dir.mkdir(exist_ok=True)
        return output_dir
    
    def get_project_clips_directory(self, project_id: str) -> Path:
        """Get project clips directory"""
        clips_dir = self.clips_directory / project_id
        clips_dir.mkdir(exist_ok=True)
        return clips_dir
    
    def get_project_collections_directory(self, project_id: str) -> Path:
        """Get project collections directory"""
        collections_dir = self.collections_directory / project_id
        collections_dir.mkdir(exist_ok=True)
        return collections_dir
    
    def get_database_path(self) -> Path:
        """Get database path"""
        return self.data_directory / "autoclip.db"
    
    def get_settings_file_path(self) -> Path:
        """Get settings file path"""
        return self.data_directory / "settings.json"
    
    def get_clip_file_path(self, project_id: str, clip_title: str, extension: str = "mp4") -> Path:
        """Get clip file path"""
        clips_dir = self.get_project_clips_directory(project_id)
        # Sanitize filename, remove special characters
        safe_title = "".join(c for c in clip_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return clips_dir / f"{safe_title}.{extension}"
    
    def get_collection_file_path(self, project_id: str, collection_title: str, extension: str = "mp4") -> Path:
        """Get collection file path"""
        collections_dir = self.get_project_collections_directory(project_id)
        # Sanitize filename, remove special characters
        safe_title = "".join(c for c in collection_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        return collections_dir / f"{safe_title}.{extension}"
    
    def get_metadata_file_path(self, project_id: str, step_name: str, filename: str) -> Path:
        """Get metadata file path"""
        metadata_dir = self.get_project_directory(project_id) / step_name
        metadata_dir.mkdir(exist_ok=True)
        return metadata_dir / filename
    
    def validate_paths(self) -> Dict[str, Any]:
        """Validate all path configurations"""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "paths": {}
        }
        
        try:
            # Check critical directories
            key_paths = {
                "project_root": self.project_root,
                "data_directory": self.data_directory,
                "output_directory": self.output_directory,
                "clips_directory": self.clips_directory,
                "collections_directory": self.collections_directory,
                "metadata_directory": self.metadata_directory,
                "projects_directory": self.projects_directory
            }
            
            for name, path in key_paths.items():
                validation_result["paths"][name] = str(path)
                
                if not path.exists():
                    validation_result["warnings"].append(f"Directory does not exist: {name} = {path}")
                elif not path.is_dir():
                    validation_result["errors"].append(f"Path is not a directory: {name} = {path}")
                    validation_result["valid"] = False
            
            # Check for duplicate or conflicting paths
            all_paths = list(validation_result["paths"].values())
            if len(all_paths) != len(set(all_paths)):
                validation_result["errors"].append("Duplicate path configurations exist")
                validation_result["valid"] = False
            
        except Exception as e:
            validation_result["errors"].append(f"Path validation failed: {str(e)}")
            validation_result["valid"] = False
        
        return validation_result
    
    def get_path_summary(self) -> Dict[str, str]:
        """Get path configuration summary"""
        return {
            "project_root": str(self.project_root),
            "data_directory": str(self.data_directory),
            "output_directory": str(self.output_directory),
            "clips_directory": str(self.clips_directory),
            "collections_directory": str(self.collections_directory),
            "metadata_directory": str(self.metadata_directory),
            "projects_directory": str(self.projects_directory),
            "uploads_directory": str(self.uploads_directory),
            "temp_directory": str(self.temp_directory),
            "backups_directory": str(self.backups_directory)
        }

# Global path manager instance
path_manager = UnifiedPathManager()

# Backward-compatible path constants
PROJECT_ROOT = path_manager.project_root
DATA_DIR = path_manager.data_directory
OUTPUT_DIR = path_manager.output_directory
CLIPS_DIR = path_manager.clips_directory
COLLECTIONS_DIR = path_manager.collections_directory
METADATA_DIR = path_manager.metadata_directory
PROJECTS_DIR = path_manager.projects_directory
UPLOADS_DIR = path_manager.uploads_directory
TEMP_DIR = path_manager.temp_directory
BACKUPS_DIR = path_manager.backups_directory

# Convenience functions
def get_project_directory(project_id: str) -> Path:
    """Get project directory"""
    return path_manager.get_project_directory(project_id)

def get_clip_file_path(project_id: str, clip_title: str, extension: str = "mp4") -> Path:
    """Get clip file path"""
    return path_manager.get_clip_file_path(project_id, clip_title, extension)

def get_collection_file_path(project_id: str, collection_title: str, extension: str = "mp4") -> Path:
    """Get collection file path"""
    return path_manager.get_collection_file_path(project_id, collection_title, extension)

def validate_paths() -> Dict[str, Any]:
    """Validate all path configurations"""
    return path_manager.validate_paths()

def get_path_summary() -> Dict[str, str]:
    """Get path configuration summary"""
    return path_manager.get_path_summary()
