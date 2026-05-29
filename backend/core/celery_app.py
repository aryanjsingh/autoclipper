"""
Celery Application Configuration
Task queue configuration and initialization
"""

import os
from celery import Celery
from celery.schedules import crontab
from pathlib import Path

# Set default configuration module
# os.environ.setdefault('CELERY_CONFIG_MODULE', 'backend.core.celery_app')

# Create Celery application
celery_app = Celery('autoclip')

# Configure Celery
class CeleryConfig:
    """Celery configuration class"""
    
    # Task serialization format
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = 'Asia/Shanghai'
    enable_utc = True
    
    # Redis configuration
    broker_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    result_backend = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Task configuration
    task_always_eager = os.getenv('CELERY_ALWAYS_EAGER', 'False').lower() == 'true'  # Async execution in production
    task_eager_propagates = True
    
    # Worker configuration
    worker_prefetch_multiplier = 1
    worker_max_tasks_per_child = 1000
    worker_disable_rate_limits = True
    
    # Task routing
    task_routes = {
        'backend.tasks.processing.*': {'queue': 'processing'},
        'backend.tasks.video.*': {'queue': 'video'},
        'backend.tasks.notification.*': {'queue': 'notification'},
        'backend.tasks.upload.*': {'queue': 'upload'},  # Add upload task routing
        'backend.tasks.import_processing.*': {'queue': 'processing'},  # Import task routing
    }
    
    # Scheduled task configuration
    beat_schedule = {
        'cleanup-expired-tasks': {
            'task': 'backend.tasks.maintenance.cleanup_expired_tasks',
            'schedule': crontab(hour=2, minute=0),  # Daily at 2:00 AM
        },
        'health-check': {
            'task': 'backend.tasks.maintenance.health_check',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes
        },
    }
    
    # Result configuration
    result_expires = 3600  # 1 hour
    task_ignore_result = False
    
    # Logging configuration
    worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
    worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s'

# Apply configuration
celery_app.config_from_object(CeleryConfig)

# Auto-discover tasks
celery_app.autodiscover_tasks([
    'backend.tasks.processing',
    'backend.tasks.video', 
    'backend.tasks.notification',
    'backend.tasks.maintenance',
    'backend.tasks.import_processing'  # Add import processing tasks
])

if __name__ == '__main__':
    celery_app.start()
