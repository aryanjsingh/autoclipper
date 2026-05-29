"""
Base Repository class
Provides common data access operations
"""

from typing import TypeVar, Generic, Optional, List, Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from ..models.base import BaseModel

# Define generic type
ModelType = TypeVar("ModelType", bound=BaseModel)

class BaseRepository(Generic[ModelType]):
    """
    Base Repository class, provides common CRUD operations
    
    Generic[ModelType]: Generic type, ModelType must be a subclass of BaseModel
    """
    
    def __init__(self, model: Type[ModelType], db: Session):
        """
        Initialize Repository
        
        Args:
            model: Model class
            db: Database session
        """
        self.model = model
        self.db = db
    
    def create(self, **kwargs) -> ModelType:
        """
        Create record
        
        Args:
            **kwargs: Model fields and values
            
        Returns:
            Created model instance
        """
        instance = self.model(**kwargs)
        self.db.add(instance)
        self.db.commit()
        self.db.refresh(instance)
        return instance
    
    def get_by_id(self, id: str) -> Optional[ModelType]:
        """
        Get record by ID
        
        Args:
            id: Record ID
            
        Returns:
            Model instance or None
        """
        return self.db.query(self.model).filter(self.model.id == id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """
        Get all records
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of model instances
        """
        return self.db.query(self.model).offset(skip).limit(limit).all()
    
    def update(self, id: str, **kwargs) -> Optional[ModelType]:
        """
        Update record
        
        Args:
            id: Record ID
            **kwargs: Fields and values to update
            
        Returns:
            Updated model instance or None
        """
        instance = self.get_by_id(id)
        if instance:
            for field, value in kwargs.items():
                if hasattr(instance, field):
                    setattr(instance, field, value)
            self.db.commit()
            self.db.refresh(instance)
        return instance
    
    def delete(self, id: str) -> bool:
        """
        Delete record
        
        Args:
            id: Record ID
            
        Returns:
            Whether deletion was successful
        """
        instance = self.get_by_id(id)
        if instance:
            self.db.delete(instance)
            self.db.commit()
            return True
        return False
    
    def count(self) -> int:
        """
        Get total record count
        
        Returns:
            Total record count
        """
        return self.db.query(self.model).count()
    
    def exists(self, id: str) -> bool:
        """
        Check if record exists
        
        Args:
            id: Record ID
            
        Returns:
            Whether record exists
        """
        return self.db.query(self.model).filter(self.model.id == id).first() is not None
    
    def find_by(self, **kwargs) -> List[ModelType]:
        """
        Find records by conditions
        
        Args:
            **kwargs: Query conditions
            
        Returns:
            List of matching model instances
        """
        filters = []
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                filters.append(getattr(self.model, field) == value)
        
        if filters:
            return self.db.query(self.model).filter(and_(*filters)).all()
        return []
    
    def find_one_by(self, **kwargs) -> Optional[ModelType]:
        """
        Find single record by conditions
        
        Args:
            **kwargs: Query conditions
            
        Returns:
            Matching model instance or None
        """
        filters = []
        for field, value in kwargs.items():
            if hasattr(self.model, field):
                filters.append(getattr(self.model, field) == value)
        
        if filters:
            return self.db.query(self.model).filter(and_(*filters)).first()
        return None
    
    def find_by_condition(self, condition) -> List[ModelType]:
        """
        Find records by custom condition
        
        Args:
            condition: SQLAlchemy query condition
            
        Returns:
            List of matching model instances
        """
        return self.db.query(self.model).filter(condition).all()
    
    def find_one_by_condition(self, condition) -> Optional[ModelType]:
        """
        Find single record by custom condition
        
        Args:
            condition: SQLAlchemy query condition
            
        Returns:
            Matching model instance or None
        """
        return self.db.query(self.model).filter(condition).first()
    
    def bulk_create(self, instances: List[Dict[str, Any]]) -> List[ModelType]:
        """
        Bulk create records
        
        Args:
            instances: List of instance data to create
            
        Returns:
            List of created model instances
        """
        created_instances = []
        for instance_data in instances:
            instance = self.model(**instance_data)
            self.db.add(instance)
            created_instances.append(instance)
        
        self.db.commit()
        
        # Refresh all instances
        for instance in created_instances:
            self.db.refresh(instance)
        
        return created_instances
    
    def bulk_update(self, instances: List[ModelType]) -> List[ModelType]:
        """
        Bulk update records
        
        Args:
            instances: List of instances to update
            
        Returns:
            List of updated model instances
        """
        for instance in instances:
            self.db.merge(instance)
        
        self.db.commit()
        return instances
    
    def bulk_delete(self, ids: List[str]) -> int:
        """
        Bulk delete records
        
        Args:
            ids: List of record IDs to delete
            
        Returns:
            Number of deleted records
        """
        deleted_count = self.db.query(self.model).filter(
            self.model.id.in_(ids)
        ).delete(synchronize_session=False)
        
        self.db.commit()
        return deleted_count
