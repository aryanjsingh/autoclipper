#!/usr/bin/env python3
"""
AutoClip Backend Server Startup Script
Resolves module import issues and ensures the server starts with the correct Python path
"""

import os
import sys
import uvicorn
from pathlib import Path

def main():
    # Get project root directory
    project_root = Path(__file__).parent.parent
    backend_dir = project_root / "backend"
    
    # Add backend directory to Python path
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    # Switch to backend directory
    os.chdir(backend_dir)
    
    print("Starting AutoClip backend service...")
    print(f"Project root: {project_root}")
    print(f"Backend directory: {backend_dir}")
    print(f"Current working directory: {os.getcwd()}")
    print("Service address: http://localhost:8000")
    print("API docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the service")
    
    # Start service
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,  # Modified port to avoid conflicts with other services
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main() 
