"""
Concurrency control manager
Handles task concurrency and lock control
"""

import logging
import threading
import time
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta

from .exceptions import ConcurrentError, ErrorCode

logger = logging.getLogger(__name__)


@dataclass
class LockInfo:
    """Lock information"""
    resource_id: str
    task_id: str
    acquired_at: datetime
    timeout: timedelta
    is_released: bool = False


class ConcurrencyManager:
    """Concurrency control manager"""
    
    def __init__(self):
        self._locks: Dict[str, LockInfo] = {}
        self._lock = threading.RLock()  # Used to protect internal state
    
    def acquire_lock(self, resource_id: str, task_id: str, timeout_seconds: int = 30) -> bool:
        """
        Acquire a lock
        
        Args:
            resource_id: Resource ID
            task_id: Task ID
            timeout_seconds: Timeout in seconds
            
        Returns:
            Whether the lock was successfully acquired
        """
        with self._lock:
            # Check if the resource is already locked
            if resource_id in self._locks:
                existing_lock = self._locks[resource_id]
                
                # Check if the lock has timed out
                if datetime.now() - existing_lock.acquired_at > existing_lock.timeout:
                    logger.warning(f"Lock has timed out, force releasing: {resource_id}")
                    self._release_lock_internal(resource_id)
                else:
                    # Check if it's the same task
                    if existing_lock.task_id == task_id:
                        logger.debug(f"Task {task_id} already holds lock: {resource_id}")
                        return True
                    else:
                        logger.warning(f"Resource {resource_id} is already locked by task {existing_lock.task_id}")
                        return False
            
            # Create new lock
            lock_info = LockInfo(
                resource_id=resource_id,
                task_id=task_id,
                acquired_at=datetime.now(),
                timeout=timedelta(seconds=timeout_seconds)
            )
            
            self._locks[resource_id] = lock_info
            logger.info(f"Task {task_id} successfully acquired lock: {resource_id}")
            return True
    
    def release_lock(self, resource_id: str, task_id: str) -> bool:
        """
        Release a lock
        
        Args:
            resource_id: Resource ID
            task_id: Task ID
            
        Returns:
            Whether the lock was successfully released
        """
        with self._lock:
            if resource_id not in self._locks:
                logger.warning(f"Attempted to release a non-existent lock: {resource_id}")
                return False
            
            lock_info = self._locks[resource_id]
            if lock_info.task_id != task_id:
                logger.warning(f"Task {task_id} attempted to release a lock it does not own: {resource_id}")
                return False
            
            return self._release_lock_internal(resource_id)
    
    def _release_lock_internal(self, resource_id: str) -> bool:
        """Internal lock release method"""
        if resource_id in self._locks:
            lock_info = self._locks[resource_id]
            lock_info.is_released = True
            del self._locks[resource_id]
            logger.info(f"Lock released: {resource_id}")
            return True
        return False
    
    def is_locked(self, resource_id: str) -> bool:
        """Check if a resource is locked"""
        with self._lock:
            if resource_id not in self._locks:
                return False
            
            lock_info = self._locks[resource_id]
            # Check if timed out
            if datetime.now() - lock_info.acquired_at > lock_info.timeout:
                self._release_lock_internal(resource_id)
                return False
            
            return True
    
    def get_lock_info(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get lock information"""
        with self._lock:
            if resource_id not in self._locks:
                return None
            
            lock_info = self._locks[resource_id]
            return {
                "resource_id": lock_info.resource_id,
                "task_id": lock_info.task_id,
                "acquired_at": lock_info.acquired_at.isoformat(),
                "timeout": lock_info.timeout.total_seconds(),
                "is_released": lock_info.is_released
            }
    
    def cleanup_expired_locks(self):
        """Clean up expired locks"""
        with self._lock:
            current_time = datetime.now()
            expired_resources = []
            
            for resource_id, lock_info in self._locks.items():
                if current_time - lock_info.acquired_at > lock_info.timeout:
                    expired_resources.append(resource_id)
            
            for resource_id in expired_resources:
                self._release_lock_internal(resource_id)
                logger.info(f"Cleaned up expired lock: {resource_id}")
    
    def get_all_locks(self) -> Dict[str, Dict[str, Any]]:
        """Get all lock information"""
        with self._lock:
            return {
                resource_id: self.get_lock_info(resource_id)
                for resource_id in self._locks.keys()
            }
    
    @contextmanager
    def lock_context(self, resource_id: str, task_id: str, timeout_seconds: int = 30):
        """
        Lock context manager
        
        Usage:
            with concurrency_manager.lock_context("project_123", "task_456"):
                # Execute operations that need lock protection
                pass
        """
        try:
            if not self.acquire_lock(resource_id, task_id, timeout_seconds):
                raise ConcurrentError(
                    f"Failed to acquire lock: {resource_id}",
                    resource=resource_id,
                    details={"task_id": task_id, "timeout": timeout_seconds}
                )
            yield
        finally:
            self.release_lock(resource_id, task_id)


class TaskScheduler:
    """Task scheduler"""
    
    def __init__(self, concurrency_manager: ConcurrencyManager):
        self.concurrency_manager = concurrency_manager
        self._running_tasks: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
    
    def can_start_task(self, project_id: str, task_id: str) -> bool:
        """Check if a task can be started"""
        resource_id = f"project_{project_id}"
        
        # Check if the project is already locked
        if self.concurrency_manager.is_locked(resource_id):
            return False
        
        # Check if the task is already running
        with self._lock:
            if task_id in self._running_tasks:
                return False
        
        return True
    
    def start_task(self, project_id: str, task_id: str, task_info: Dict[str, Any]) -> bool:
        """Start a task"""
        resource_id = f"project_{project_id}"
        
        if not self.can_start_task(project_id, task_id):
            return False
        
        # Acquire lock
        if not self.concurrency_manager.acquire_lock(resource_id, task_id):
            return False
        
        # Record running task
        with self._lock:
            self._running_tasks[task_id] = {
                "project_id": project_id,
                "task_id": task_id,
                "started_at": datetime.now(),
                "task_info": task_info
            }
        
        logger.info(f"Task started: {task_id} (project: {project_id})")
        return True
    
    def finish_task(self, project_id: str, task_id: str):
        """Finish a task"""
        resource_id = f"project_{project_id}"
        
        # Release lock
        self.concurrency_manager.release_lock(resource_id, task_id)
        
        # Remove running task record
        with self._lock:
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
        
        logger.info(f"Task completed: {task_id} (project: {project_id})")
    
    def get_running_tasks(self) -> Dict[str, Dict[str, Any]]:
        """Get running tasks"""
        with self._lock:
            return self._running_tasks.copy()
    
    def is_task_running(self, task_id: str) -> bool:
        """Check if a task is running"""
        with self._lock:
            return task_id in self._running_tasks


# Global concurrency manager instance
concurrency_manager = ConcurrencyManager()
task_scheduler = TaskScheduler(concurrency_manager)


def with_concurrency_control(resource_id_func: Callable = None):
    """
    Concurrency control decorator
    
    Args:
        resource_id_func: Function to generate resource ID, defaults to using project_id
        
    Usage:
        @with_concurrency_control()
        def process_project(project_id: str, task_id: str, ...):
            # Function body
            pass
        
        @with_concurrency_control(lambda ctx: f"custom_{ctx.project_id}")
        def custom_process(ctx: ProcessingContext):
            # Function body
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Try to extract project_id and task_id from arguments
            project_id = None
            task_id = None
            context = None
            
            # Check for ProcessingContext argument
            for arg in args:
                if hasattr(arg, 'project_id') and hasattr(arg, 'task_id'):
                    context = arg
                    project_id = context.project_id
                    task_id = context.task_id
                    break
            
            # If context not found, try to get from kwargs
            if not project_id:
                project_id = kwargs.get('project_id')
                task_id = kwargs.get('task_id')
            
            # If still not found, try to use the first argument as project_id
            if not project_id and len(args) > 0:
                project_id = str(args[0])
                # Generate a temporary task_id
                task_id = f"temp_task_{project_id}"
            
            if not project_id:
                raise ValueError("Unable to determine project_id and task_id")
            
            # Generate resource ID
            if resource_id_func:
                resource_id = resource_id_func(context or project_id)
            else:
                resource_id = f"project_{project_id}"
            
            # Check if the task can be started
            if not task_scheduler.can_start_task(project_id, task_id):
                raise ConcurrentError(
                    f"Project {project_id} is being processed by another task",
                    resource=resource_id,
                    details={"project_id": project_id, "task_id": task_id}
                )
            
            # Start task
            if not task_scheduler.start_task(project_id, task_id, {"function": func.__name__}):
                raise ConcurrentError(
                    f"Failed to start task: {task_id}",
                    resource=resource_id,
                    details={"project_id": project_id, "task_id": task_id}
                )
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                return result
            finally:
                # Finish task
                task_scheduler.finish_task(project_id, task_id)
        
        return wrapper
    return decorator 
