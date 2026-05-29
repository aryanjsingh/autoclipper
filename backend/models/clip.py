"""
Clip model
Defines basic information and status of video clips
"""

import enum
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum, JSON, DateTime, Text
from sqlalchemy.orm import relationship
from .base import BaseModel

class ClipStatus(str, enum.Enum):
    """Clip status enumeration"""
    PENDING = "pending"           # Pending
    PROCESSING = "processing"     # Processing
    COMPLETED = "completed"       # Completed
    FAILED = "failed"            # Failed

class Clip(BaseModel):
    """Clip model"""
    
    __tablename__ = "clips"
    
    # Basic information
    title = Column(
        String(255), 
        nullable=False, 
        comment="Clip title"
    )
    description = Column(
        Text, 
        nullable=True, 
        comment="Clip description"
    )
    
    # Status information
    status = Column(
        Enum(ClipStatus), 
        default=ClipStatus.PENDING,
        nullable=False,
        comment="Clip status"
    )
    
    # Time information
    start_time = Column(
        Integer, 
        nullable=False, 
        comment="Start time (seconds)"
    )
    end_time = Column(
        Integer, 
        nullable=False, 
        comment="End time (seconds)"
    )
    duration = Column(
        Integer, 
        nullable=False, 
        comment="Clip duration (seconds)"
    )
    
    # Score information
    score = Column(
        Float, 
        nullable=True, 
        comment="Clip score"
    )
    recommendation_reason = Column(
        Text, 
        nullable=True, 
        comment="Recommendation reason"
    )
    
    # File information
    video_path = Column(
        String(500), 
        nullable=True, 
        comment="Clip video file path"
    )
    thumbnail_path = Column(
        String(500), 
        nullable=True, 
        comment="Thumbnail file path"
    )
    
    # Processing information
    processing_step = Column(
        Integer, 
        nullable=True, 
        comment="Processing step (1-6)"
    )
    
    # Tags and metadata
    tags = Column(
        JSON, 
        nullable=True, 
        comment="Clip tags"
    )
    clip_metadata = Column(
        JSON, 
        nullable=True, 
        comment="Clip metadata (simplified version, full data stored in filesystem)"
    )
    
    # Computed properties
    @property
    def metadata_file_path(self) -> Optional[str]:
        """Get full metadata file path"""
        if self.clip_metadata and 'metadata_file' in self.clip_metadata:
            return self.clip_metadata['metadata_file']
        return None
    
    @property
    def has_full_content(self) -> bool:
        """Whether there is a full content file"""
        return self.metadata_file_path is not None
    
    # Foreign key associations
    project_id = Column(
        String(36), 
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        comment="Associated project ID"
    )
    
    # Relationships
    project = relationship(
        "Project", 
        back_populates="clips"
    )
    collections = relationship(
        "Collection", 
        secondary="clip_collection",
        back_populates="clips"
    )
    
    def __repr__(self):
        return f"<Clip(id={self.id}, title='{self.title}', duration={self.duration}s)>"
    
    @property
    def is_processing(self):
        """Whether currently processing"""
        return self.status == ClipStatus.PROCESSING
    
    @property
    def is_completed(self):
        """Whether completed"""
        return self.status == ClipStatus.COMPLETED
    
    @property
    def has_error(self):
        """Whether there is an error"""
        return self.status == ClipStatus.FAILED
    
    def get_time_range(self) -> str:
        """Get time range string"""
        try:
            start_time = int(self.start_time) if self.start_time else 0
            end_time = int(self.end_time) if self.end_time else 0
            start_min, start_sec = divmod(start_time, 60)
            end_min, end_sec = divmod(end_time, 60)
            return f"{start_min:02d}:{start_sec:02d} - {end_min:02d}:{end_sec:02d}"
        except (TypeError, ValueError):
            return "00:00 - 00:00"
    
    def calculate_duration(self):
        """Calculate clip duration"""
        self.duration = self.end_time - self.start_time
        return self.duration
