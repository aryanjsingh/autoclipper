"""
Repository Factory
Provides unified Repository instantiation and management
"""

from typing import Dict, Type
from sqlalchemy.orm import Session
from ..repositories.base import BaseRepository
from ..repositories.project_repository import ProjectRepository
from ..repositories.clip_repository import ClipRepository
from ..repositories.collection_repository import CollectionRepository
from ..repositories.task_repository import TaskRepository

class RepositoryFactory:
    """Repository Factory class"""
    
    def __init__(self, db: Session):
        """
        Initialize Repository Factory
        
        Args:
            db: Database session
        """
        self.db = db
        self._repositories: Dict[str, BaseRepository] = {}
    
    def get_project_repository(self) -> ProjectRepository:
        """Get project Repository"""
        if "project" not in self._repositories:
            self._repositories["project"] = ProjectRepository(self.db)
        return self._repositories["project"]
    
    def get_clip_repository(self) -> ClipRepository:
        """Get clip Repository"""
        if "clip" not in self._repositories:
            self._repositories["clip"] = ClipRepository(self.db)
        return self._repositories["clip"]
    
    def get_collection_repository(self) -> CollectionRepository:
        """Get collection Repository"""
        if "collection" not in self._repositories:
            self._repositories["collection"] = CollectionRepository(self.db)
        return self._repositories["collection"]
    
    def get_task_repository(self) -> TaskRepository:
        """Get task Repository"""
        if "task" not in self._repositories:
            self._repositories["task"] = TaskRepository(self.db)
        return self._repositories["task"]
    
    def get_repository(self, repository_type: str) -> BaseRepository:
        """
        Get Repository by type
        
        Args:
            repository_type: Repository type
            
        Returns:
            Repository instance
        """
        repository_map = {
            "project": self.get_project_repository,
            "clip": self.get_clip_repository,
            "collection": self.get_collection_repository,
            "task": self.get_task_repository
        }
        
        if repository_type not in repository_map:
            raise ValueError(f"Unknown repository type: {repository_type}")
        
        return repository_map[repository_type]()
    
    def clear_cache(self):
        """Clear Repository cache"""
        self._repositories.clear()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.clear_cache()

# Global Repository Factory instance
_repository_factory: RepositoryFactory = None

def get_repository_factory(db: Session) -> RepositoryFactory:
    """
    Get Repository Factory instance
    
    Args:
        db: Database session
        
    Returns:
        Repository Factory instance
    """
    global _repository_factory
    if _repository_factory is None or _repository_factory.db != db:
        _repository_factory = RepositoryFactory(db)
    return _repository_factory

def get_project_repository(db: Session) -> ProjectRepository:
    """
    Get project Repository
    
    Args:
        db: Database session
        
    Returns:
        Project Repository instance
    """
    return get_repository_factory(db).get_project_repository()

def get_clip_repository(db: Session) -> ClipRepository:
    """
    Get clip Repository
    
    Args:
        db: Database session
        
    Returns:
        Clip Repository instance
    """
    return get_repository_factory(db).get_clip_repository()

def get_collection_repository(db: Session) -> CollectionRepository:
    """
    Get collection Repository
    
    Args:
        db: Database session
        
    Returns:
        Collection Repository instance
    """
    return get_repository_factory(db).get_collection_repository()

def get_task_repository(db: Session) -> TaskRepository:
    """
    Get task Repository
    
    Args:
        db: Database session
        
    Returns:
        Task Repository instance
    """
    return get_repository_factory(db).get_task_repository() 
