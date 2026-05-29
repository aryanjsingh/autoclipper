"""
Periodic task scheduler
Configure and manage periodically executed maintenance tasks
"""

import logging
from celery import Celery
from celery.schedules import crontab

from ..core.celery_app import celery_app

logger = logging.getLogger(__name__)


# Configure periodic tasks
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """Configure periodic tasks"""
    
    # Execute data cleanup daily at 2 AM
    sender.add_periodic_task(
        crontab(hour=2, minute=0),
        cleanup_expired_data.s(days=30),
        name='daily_data_cleanup'
    )
    
    # Execute data consistency check hourly
    sender.add_periodic_task(
        crontab(minute=0),
        check_data_consistency.s(),
        name='hourly_consistency_check'
    )
    
    # Execute orphaned data cleanup weekly at 3 AM on Sunday
    sender.add_periodic_task(
        crontab(hour=3, minute=0, day_of_week=0),
        cleanup_orphaned_data.s(),
        name='weekly_orphaned_cleanup'
    )
    
    # Execute system health check daily at 1 AM
    sender.add_periodic_task(
        crontab(hour=1, minute=0),
        health_check.s(),
        name='daily_health_check'
    )
    
    logger.info("Periodic tasks configured")


def get_scheduled_tasks() -> dict:
    """Get all configured periodic tasks"""
    return {
        'daily_data_cleanup': {
            'schedule': 'Daily at 2 AM',
            'task': 'cleanup_expired_data',
            'description': 'Clean up expired data (retain 30 days)'
        },
        'hourly_consistency_check': {
            'schedule': 'Hourly',
            'task': 'check_data_consistency',
            'description': 'Check data consistency'
        },
        'weekly_orphaned_cleanup': {
            'schedule': 'Weekly at 3 AM on Sunday',
            'task': 'cleanup_orphaned_data',
            'description': 'Clean up orphaned data'
        },
        'daily_health_check': {
            'schedule': 'Daily at 1 AM',
            'task': 'health_check',
            'description': 'System health check'
        }
    }


def enable_scheduled_tasks():
    """Enable periodic tasks"""
    try:
        # Here you can add logic to enable periodic tasks
        logger.info("Periodic tasks enabled")
        return True
    except Exception as e:
        logger.error(f"Failed to enable periodic tasks: {e}")
        return False


def disable_scheduled_tasks():
    """Disable periodic tasks"""
    try:
        # Here you can add logic to disable periodic tasks
        logger.info("Periodic tasks disabled")
        return True
    except Exception as e:
        logger.error(f"Failed to disable periodic tasks: {e}")
        return False
