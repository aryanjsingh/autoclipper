"""
Async task manager
Prevents uncaught exceptions from causing backend restarts
"""

import asyncio
import logging
from typing import Callable, Any, Dict, Optional
import traceback
from datetime import datetime

logger = logging.getLogger(__name__)

class AsyncTaskManager:
    """Async task manager"""
    
    def __init__(self):
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_results: Dict[str, Any] = {}
    
    async def create_safe_task(
        self, 
        task_id: str, 
        coro: Callable, 
        *args, 
        **kwargs
    ) -> asyncio.Task:
        """
        Create a safe async task that prevents uncaught exceptions
        
        Args:
            task_id: Task ID
            coro: Coroutine function
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Async task object
        """
        
        async def safe_wrapper():
            """Safe wrapper that catches all exceptions"""
            try:
                logger.info(f"Starting task: {task_id}")
                result = await coro(*args, **kwargs)
                self.task_results[task_id] = {
                    "status": "completed",
                    "result": result,
                    "completed_at": datetime.now().isoformat()
                }
                logger.info(f"Task completed: {task_id}")
                return result
                
            except Exception as e:
                error_info = {
                    "status": "failed",
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "traceback": traceback.format_exc(),
                    "failed_at": datetime.now().isoformat()
                }
                self.task_results[task_id] = error_info
                logger.error(f"Task failed: {task_id}, error: {e}")
                logger.error(f"Error details: {traceback.format_exc()}")
                
                # Do not re-raise exception to avoid affecting the main event loop
                return error_info
        
        # Create task
        task = asyncio.create_task(safe_wrapper())
        self.running_tasks[task_id] = task
        
        # Add completion callback
        task.add_done_callback(lambda t: self._cleanup_task(task_id))
        
        return task
    
    def _cleanup_task(self, task_id: str):
        """Clean up completed tasks"""
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
        logger.debug(f"Task cleaned up: {task_id}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            return {
                "status": "running",
                "task_id": task_id,
                "created_at": "unknown"  # Can be extended to record creation time
            }
        elif task_id in self.task_results:
            return self.task_results[task_id]
        else:
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel task"""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            logger.info(f"Task cancelled: {task_id}")
            return True
        return False
    
    def get_all_tasks(self) -> Dict[str, Any]:
        """Get all task statuses"""
        all_tasks = {}
        
        # Running tasks
        for task_id, task in self.running_tasks.items():
            all_tasks[task_id] = {
                "status": "running",
                "task_id": task_id
            }
        
        # Completed tasks
        for task_id, result in self.task_results.items():
            all_tasks[task_id] = result
        
        return all_tasks

# Global task manager instance
task_manager = AsyncTaskManager()

# Decorator function
def safe_async_task(task_id: str):
    """
    Decorator: wrap a function as a safe async task
    
    Usage:
        @safe_async_task("my_task")
        async def my_function():
            # Function implementation
            pass
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            return await task_manager.create_safe_task(task_id, func, *args, **kwargs)
        return wrapper
    return decorator

# Usage example
async def example_usage():
    """Usage example"""
    
    async def risky_task():
        """A task that might fail"""
        await asyncio.sleep(1)
        # Simulate potential exception
        if True:  # Can be changed to False to test normal case
            raise ValueError("Simulated error")
        return "Task completed"
    
    # Create safe task
    task = await task_manager.create_safe_task("example_task", risky_task)
    
    # Wait for task completion
    result = await task
    print(f"Task result: {result}")
    
    # Check task status
    status = task_manager.get_task_status("example_task")
    print(f"Task status: {status}")

if __name__ == "__main__":
    asyncio.run(example_usage())
