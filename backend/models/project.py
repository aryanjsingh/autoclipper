"""
Project model
Defines basic information and status of a project
"""

import enum
from typing import Optional
from sqlalchemy import Column, String, Text, JSON, Enum, Integer, DateTime
from sqlalchemy.orm import relationship
from .base import BaseModel

class ProjectStatus(str, enum.Enum):
    """Project status enumeration"""
    PENDING = "pending"           # Pending
    PROCESSING = "processing"     # Processing
    COMPLETED = "completed"       # Completed
    FAILED = "failed"            # Failed

class ProjectType(str, enum.Enum):
    """Project type enumeration"""
    DEFAULT = "default"           # Default
    KNOWLEDGE = "knowledge"       # Knowledge/Science
    BUSINESS = "business"         # Business/Finance
    OPINION = "opinion"          # Opinion/Commentary
    EXPERIENCE = "experience"    # Experience Sharing
    SPEECH = "speech"            # Speech/Talk Show
    CONTENT_REVIEW = "content_review"  # Content Review
    ENTERTAINMENT = "entertainment"    # Entertainment

class Project(BaseModel):
    """Project model"""
    
    __tablename__ = "projects"
    
    # Basic information
    name = Column(
        String(255), 
        nullable=False, 
        comment="Project name"
    )
    description = Column(
        Text, 
        nullable=True, 
        comment="Project description"
    )
    
    # Status information
    status = Column(
        Enum(ProjectStatus), 
        default=ProjectStatus.PENDING,
        nullable=False,
        comment="Project status"
    )
    
    # Project type
    project_type = Column(
        Enum(ProjectType), 
        default=ProjectType.DEFAULT,
        nullable=False,
        comment="Project type"
    )
    video_path = Column(
        String(500), 
        nullable=True, 
        comment="Video file path"
    )
    subtitle_path = Column(
        String(500), 
        nullable=True, 
        comment="Subtitle file path"
    )
    video_duration = Column(
        Integer, 
        nullable=True, 
        comment="Video duration (seconds)"
    )
    thumbnail = Column(
        Text, 
        nullable=True, 
        comment="Project thumbnail (base64 encoded)"
    )
    
    # Processing configuration
    processing_config = Column(
        JSON, 
        nullable=True, 
        comment="Processing configuration parameters"
    )
    
    # Metadata
    project_metadata = Column(
        JSON, 
        nullable=True, 
        comment="Project metadata (simplified version, full data stored in filesystem)"
    )
    
    # Computed properties
    @property
    def storage_initialized(self) -> bool:
        """Whether storage service is initialized"""
        if self.project_metadata and 'storage_service_initialized' in self.project_metadata:
            return self.project_metadata['storage_service_initialized']
        return False
    
    @property
    def has_video_file(self) -> bool:
        """Whether there is a video file"""
        return self.video_path is not None
    
    @property
    def has_subtitle_file(self) -> bool:
        """Whether there is a subtitle file"""
        return self.subtitle_path is not None
    
    # Completion time
    completed_at = Column(
        DateTime, 
        nullable=True, 
        comment="Project completion time"
    )
    
    # Relationships
    clips = relationship(
        "Clip", 
        back_populates="project",
        cascade="all, delete-orphan"
    )
    collections = relationship(
        "Collection", 
        back_populates="project",
        cascade="all, delete-orphan"
    )
    tasks = relationship(
        "Task", 
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self):
        return f"<Project(id={self.id}, name='{self.name}', status={self.status})>"
    
    @property
    def clips_count(self):
        """Get number of clips"""
        return len(self.clips) if self.clips else 0
    
    @property
    def collections_count(self):
        """Get number of collections"""
        return len(self.collections) if self.collections else 0
    
    @property
    def is_processing(self):
        """Whether currently processing"""
        return self.status == ProjectStatus.PROCESSING
    
    @property
    def is_completed(self):
        """Whether completed"""
        return self.status == ProjectStatus.COMPLETED
    
    @property
    def has_error(self):
        """Whether there is an error"""
        return self.status == ProjectStatus.FAILED
