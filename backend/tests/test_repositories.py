"""
Repository pattern tests
Verify data access layer functionality
"""

import sys, os
# Add project root directory to sys.path to ensure backend package can be found
current_file = os.path.abspath(__file__)
backend_dir = os.path.dirname(os.path.dirname(current_file))  # backend directory
project_root = os.path.dirname(backend_dir)  # autoclip root directory

# Add project root directory to sys.path so Python can find backend package
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from repositories.factory import (
    get_project_repository,
    get_clip_repository,
    get_collection_repository,
    get_task_repository
)
from backend.core.database import get_db, init_database, reset_database
from backend.models.project import ProjectStatus, ProjectType
from backend.models.clip import ClipStatus
from backend.models.collection import CollectionStatus
from backend.models.task import TaskStatus, TaskType

class TestRepositoryPattern:
    """Repository pattern test class"""
    
    @pytest.fixture(autouse=True)
    def setup_database(self):
        """Set up test database"""
        # Reset database to ensure clean test environment
        reset_database()
        # Initialize database
        init_database()
        yield
        # Clean up database after test
        reset_database()
    
    def test_project_repository_crud(self):
        """Test project Repository CRUD operations"""
        db = next(get_db())
        project_repo = get_project_repository(db)
        
        # Create project
        project_data = {
            "name": "Test project",
            "description": "This is a test project",
            "project_type": ProjectType.KNOWLEDGE,
            "status": ProjectStatus.PENDING
        }
        
        project = project_repo.create(**project_data)
        assert project.id is not None
        assert project.name == "Test project"
        assert project.status == ProjectStatus.PENDING
        
        # Query project
        retrieved_project = project_repo.get_by_id(project.id)
        assert retrieved_project is not None
        assert retrieved_project.name == "Test project"
        
        # Update project
        updated_project = project_repo.update(project.id, status=ProjectStatus.PROCESSING)
        assert updated_project.status == ProjectStatus.PROCESSING
        
        # Delete project
        success = project_repo.delete(project.id)
        assert success is True
        
        # Verify deletion
        deleted_project = project_repo.get_by_id(project.id)
        assert deleted_project is None
    
    def test_clip_repository_operations(self):
        """Test clip Repository operations"""
        db = next(get_db())
        project_repo = get_project_repository(db)
        clip_repo = get_clip_repository(db)
        
        # Create project
        project = project_repo.create(
            name="Test project",
            project_type=ProjectType.KNOWLEDGE,
            status=ProjectStatus.PENDING
        )
        
        # Create clip
        clip_data = {
            "project_id": project.id,
            "title": "Test clip",
            "description": "This is a test clip",
            "start_time": 0,
            "end_time": 60,
            "duration": 60,
            "score": 0.8,
            "status": ClipStatus.COMPLETED
        }
        
        clip = clip_repo.create(**clip_data)
        assert clip.project_id == project.id
        assert clip.title == "Test clip"
        
        # Test querying clips by project
        project_clips = clip_repo.get_by_project(project.id)
        assert len(project_clips) == 1
        assert project_clips[0].id == clip.id
        
        # Test querying clips by status
        completed_clips = clip_repo.get_by_status(ClipStatus.COMPLETED)
        assert len(completed_clips) == 1
        assert completed_clips[0].id == clip.id
        
        # Test high-scoring clips query
        high_score_clips = clip_repo.get_high_score_clips(project.id, min_score=0.7)
        assert len(high_score_clips) == 1
        assert high_score_clips[0].id == clip.id
    
    def test_collection_repository_operations(self):
        """Test collection Repository operations"""
        db = next(get_db())
        project_repo = get_project_repository(db)
        collection_repo = get_collection_repository(db)
        
        # Create project
        project = project_repo.create(
            name="Test project",
            project_type=ProjectType.KNOWLEDGE,
            status=ProjectStatus.PENDING
        )
        
        # Create collection
        collection_data = {
            "project_id": project.id,
            "name": "Test collection",
            "description": "This is a test collection",
            "theme": "Test theme",
            "clips_count": 5,
            "total_duration": 300,
            "status": CollectionStatus.COMPLETED
        }
        
        collection = collection_repo.create(**collection_data)
        assert collection.project_id == project.id
        assert collection.name == "Test collection"
        
        # Test querying collections by project
        project_collections = collection_repo.get_by_project(project.id)
        assert len(project_collections) == 1
        assert project_collections[0].id == collection.id
        
        # Test querying collections by theme
        theme_collections = collection_repo.get_by_theme(project.id, "Test theme")
        assert len(theme_collections) == 1
        assert theme_collections[0].id == collection.id
    
    def test_task_repository_operations(self):
        """Test task Repository operations"""
        db = next(get_db())
        project_repo = get_project_repository(db)
        task_repo = get_task_repository(db)
        
        # Create project
        project = project_repo.create(
            name="Test project",
            project_type=ProjectType.KNOWLEDGE,
            status=ProjectStatus.PENDING
        )
        
        # Create task
        task_data = {
            "project_id": project.id,
            "name": "Test task",
            "description": "This is a test task",
            "task_type": TaskType.VIDEO_PROCESSING,
            "status": TaskStatus.PENDING,
            "priority": 1
        }
        
        task = task_repo.create(**task_data)
        assert task.project_id == project.id
        assert task.name == "Test task"
        assert task.status == TaskStatus.PENDING
        
        # Test task status update
        task_repo.update_task_status(task.id, TaskStatus.RUNNING)
        updated_task = task_repo.get_by_id(task.id)
        assert updated_task.status == TaskStatus.RUNNING
        
        # Test task completion
        task_repo.update_task_status(task.id, TaskStatus.COMPLETED)
        completed_task = task_repo.get_by_id(task.id)
        assert completed_task.status == TaskStatus.COMPLETED
        
        # Test querying tasks by project
        project_tasks = task_repo.get_by_project(project.id)
        assert len(project_tasks) == 1
        assert project_tasks[0].id == task.id
    
    def test_repository_statistics(self):
        """Test Repository statistics functionality"""
        db = next(get_db())
        project_repo = get_project_repository(db)
        clip_repo = get_clip_repository(db)
        collection_repo = get_collection_repository(db)
        task_repo = get_task_repository(db)
        
        # Create project
        project = project_repo.create(
            name="Statistics test project",
            project_type=ProjectType.KNOWLEDGE,
            status=ProjectStatus.COMPLETED
        )
        
        # Create multiple clips
        for i in range(5):
            clip_repo.create(
                project_id=project.id,
                title=f"Clip {i+1}",
                start_time=i*60,
                end_time=(i+1)*60,
                duration=60,
                score=0.7 + i*0.1,
                status=ClipStatus.COMPLETED
            )
        
        # Create multiple collections
        for i in range(3):
            collection_repo.create(
                project_id=project.id,
                name=f"Collection {i+1}",
                theme=f"Theme {i+1}",
                clips_count=2,
                total_duration=120,
                status=CollectionStatus.COMPLETED
            )
        
        # Create multiple tasks
        for i in range(6):
            task_repo.create(
                project_id=project.id,
                name=f"Task {i+1}",
                            task_type=TaskType.VIDEO_PROCESSING,
            status=TaskStatus.COMPLETED if i < 5 else TaskStatus.FAILED
            )
        
        # Test project statistics
        project_stats = project_repo.get_project_statistics()
        assert project_stats["total"] >= 1
        assert project_stats["completed"] >= 1
        
        # Test clip statistics
        clip_stats = clip_repo.get_clips_statistics(project.id)
        assert clip_stats["total"] == 5
        assert clip_stats["completed"] == 5
        assert clip_stats["avg_score"] > 0.7
        
        # Test collection statistics
        collection_stats = collection_repo.get_collections_statistics(project.id)
        assert collection_stats["total"] == 3
        assert collection_stats["completed"] == 3
        
        # Test task statistics
        task_stats = task_repo.get_tasks_statistics(project.id)
        assert task_stats["total"] == 6
        assert task_stats["completed"] == 5
        assert task_stats["failed"] == 1
    
    def test_repository_search(self):
        """Test Repository search functionality"""
        db = next(get_db())
        project_repo = get_project_repository(db)
        clip_repo = get_clip_repository(db)
        
        # Create project
        project = project_repo.create(
            name="Search test project",
            description="This is a project for search testing",
            project_type=ProjectType.KNOWLEDGE,
            status=ProjectStatus.PENDING
        )
        
        # Create clip
        clip_repo.create(
            project_id=project.id,
            title="Clip containing keywords",
            description="This clip contains important keywords",
            start_time=0,
            end_time=60,
            duration=60,
            status=ClipStatus.COMPLETED
        )
        
        # Test project search
        search_results = project_repo.search_projects("Search test")
        assert len(search_results) == 1
        assert search_results[0].id == project.id
        
        # Test clip search
        clip_results = clip_repo.search_clips(project.id, "keywords")
        assert len(clip_results) == 1
        assert "keywords" in clip_results[0].title or "keywords" in clip_results[0].description

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 
