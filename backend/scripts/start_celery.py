#!/usr/bin/env python3
"""
Celery startup script
Start Celery Worker and Beat scheduler
"""

import os
import sys
import subprocess
import signal
import time
from pathlib import Path

# Add project root directory to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def start_celery_worker():
    """Start Celery Worker"""
    print("Starting Celery Worker...")
    
    cmd = [
        "celery", "-A", "backend.core.celery_app", "worker",
        "--loglevel=info",
        "--concurrency=2",
        "--queues=processing,video,notification,maintenance",
        "--hostname=worker1@%h"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=str(project_root))
        print(f"Celery Worker started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"Failed to start Celery Worker: {e}")
        return None

def start_celery_beat():
    """Start Celery Beat scheduler"""
    print("Starting Celery Beat scheduler...")
    
    cmd = [
        "celery", "-A", "backend.core.celery_app", "beat",
        "--loglevel=info",
        "--schedule=/tmp/celerybeat-schedule",
        "--pidfile=/tmp/celerybeat.pid"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=str(project_root))
        print(f"Celery Beat started (PID: {process.pid})")
        return process
    except Exception as e:
        print(f"Failed to start Celery Beat: {e}")
        return None

def start_flower():
    """Start Flower monitoring interface"""
    print("Starting Flower monitoring interface...")
    
    cmd = [
        "celery", "-A", "backend.core.celery_app", "flower",
        "--port=5555",
        "--loglevel=info"
    ]
    
    try:
        process = subprocess.Popen(cmd, cwd=str(project_root))
        print(f"Flower started (PID: {process.pid})")
        print("Flower monitoring interface: http://localhost:5555")
        return process
    except Exception as e:
        print(f"Failed to start Flower: {e}")
        return None

def signal_handler(signum, frame):
    """Signal handler function"""
    print("\nReceived stop signal, shutting down services...")
    sys.exit(0)

def main():
    """Main function"""
    print("AutoClip Celery Task Queue Launcher")
    print("=" * 50)
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Check Redis connection
    try:
        import redis
        r = redis.Redis.from_url('redis://localhost:6379/0')
        r.ping()
        print("Redis connection normal")
    except Exception as e:
        print(f"Redis connection failed: {e}")
        print("Please ensure Redis service is running: redis-server")
        return
    
    # Start services
    processes = []
    
    # Start Worker
    worker_process = start_celery_worker()
    if worker_process:
        processes.append(worker_process)
    
    # Start Beat
    beat_process = start_celery_beat()
    if beat_process:
        processes.append(beat_process)
    
    # Start Flower
    flower_process = start_flower()
    if flower_process:
        processes.append(flower_process)
    
    if not processes:
        print("No services started successfully")
        return
    
    print("\nAll services started!")
    print("Service status:")
    print("   - Celery Worker: Processing tasks")
    print("   - Celery Beat: Scheduled task dispatch")
    print("   - Flower: Task monitoring interface (http://localhost:5555)")
    print("\nPress Ctrl+C to stop all services")
    
    try:
        # Wait for processes
        while True:
            time.sleep(1)
            # Check if processes are still running
            for process in processes:
                if process.poll() is not None:
                    print(f"Process {process.pid} has exited")
    except KeyboardInterrupt:
        print("\nStopping services...")
    finally:
        # Stop all processes
        for process in processes:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                print(f"Process {process.pid} stopped")

if __name__ == "__main__":
    main() 
