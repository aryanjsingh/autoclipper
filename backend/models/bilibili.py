"""
Bilibili-related database models
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from .base import Base


class BilibiliAccount(Base):
    """Bilibili account table"""
    __tablename__ = "bilibili_accounts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), nullable=False, unique=True)
    nickname = Column(String(100))
    cookies = Column(Text)  # Encrypted cookies storage
    status = Column(String(20), default="active")  # active/inactive/banned
    is_default = Column(Boolean, default=False)
    
    # Account information
    uid = Column(String(50))  # Bilibili user ID
    level = Column(Integer, default=0)  # User level
    is_vip = Column(Boolean, default=False)  # Whether VIP
    can_upload = Column(Boolean, default=True)  # Whether can upload
    
    # Usage statistics
    last_used_at = Column(DateTime)  # Last used time
    upload_count = Column(Integer, default=0)  # Upload count
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    upload_records = relationship("BilibiliUploadRecord", back_populates="account")


class BilibiliUploadRecord(Base):
    """Bilibili upload record table"""
    __tablename__ = "bilibili_upload_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(100), unique=True, index=True)  # Task queue ID
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=True)
    account_id = Column(Integer, ForeignKey("bilibili_accounts.id"), nullable=False)
    clip_id = Column(String(255))  # Clip ID
    
    # Upload content
    title = Column(String(200), nullable=False)
    description = Column(Text)
    tags = Column(Text)  # JSON string storage
    partition_id = Column(Integer, default=17)  # Partition ID, default single-player game
    video_path = Column(String(500))  # Video file path
    
    # Upload result
    bv_id = Column(String(20))  # BV number after successful upload
    av_id = Column(String(20))  # AV number
    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    error_message = Column(Text)  # Error message
    
    # Upload progress and statistics
    progress = Column(Integer, default=0)  # Upload progress 0-100
    file_size = Column(Integer)  # File size (bytes)
    upload_duration = Column(Integer)  # Upload duration (seconds)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    account = relationship("BilibiliAccount", back_populates="upload_records")

# For backward compatibility, keep the old class name
UploadRecord = BilibiliUploadRecord
