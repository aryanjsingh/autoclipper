#!/bin/bash

# Docker development environment startup script
# Specifically designed for development environment

set -euo pipefail

echo "🚀 Starting AutoClip development environment..."

# Set environment variables
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# Ensure data directories exist
mkdir -p /app/data/projects /app/data/uploads /app/data/temp /app/data/output /app/logs

# Activate virtual environment
source /app/venv/bin/activate

# Return to root directory
cd /app

# Start backend service
echo "🔧 Starting backend service..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
