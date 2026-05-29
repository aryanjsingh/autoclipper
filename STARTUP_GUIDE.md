# AutoClip System Startup Guide

## 📋 Overview

AutoClip is an AI-powered video clipping processing system with a frontend-backend separation architecture. This guide will help you quickly start and run the entire system.

## 🚀 Quick Start

### 1. One-Click Startup (Recommended)

```bash
# Full startup (includes detailed checks and health monitoring)
./start_autoclip.sh

# Quick startup (development environment, skips detailed checks)
./quick_start.sh
```

### 2. System Management

```bash
# Check system status
./status_autoclip.sh

# Stop all services
./stop_autoclip.sh
```

## 📊 System Architecture

### Backend Services
- **FastAPI**: RESTful API and WebSocket support
- **Celery**: Asynchronous task queue
- **Redis**: Message broker and cache
- **SQLite**: Data storage

### Frontend Services
- **React**: User interface
- **Vite**: Development server
- **TypeScript**: Type safety

## 🔧 Environment Requirements

### System Requirements
- macOS or Linux
- Python 3.8+
- Node.js 16+
- Redis server

### Dependency Installation

```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend
npm install
cd ..

# 4. Install Redis (macOS)
brew install redis
brew services start redis

# 5. Configure environment variables
cp env.example .env
# Edit .env file and fill in necessary configurations
```

## 📝 Configuration Files

### Environment Variables (.env)

```bash
# Database configuration
DATABASE_URL=sqlite:///./data/autoclip.db

# Redis configuration
REDIS_URL=redis://localhost:6379/0

# API configuration
API_DASHSCOPE_API_KEY=your_api_key_here
API_MODEL_NAME=qwen-plus

# Logging configuration
LOG_LEVEL=INFO
ENVIRONMENT=development
DEBUG=true
```

## 🌐 Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Frontend Interface | 3000 | React development server |
| Backend API | 8000 | FastAPI server |
| Redis | 6379 | Message broker |
| API Documentation | 8000/docs | Swagger UI |

## 📁 Directory Structure

```
autoclip/
├── backend/                 # Backend code
│   ├── api/                # API routes
│   ├── core/               # Core configuration
│   ├── models/             # Data models
│   ├── services/           # Business logic
│   └── tasks/              # Celery tasks
├── frontend/               # Frontend code
│   ├── src/                # Source code
│   └── public/             # Static resources
├── data/                   # Data storage
│   ├── projects/           # Project data
│   └── uploads/            # Uploaded files
├── logs/                   # Log files
├── scripts/                # Utility scripts
└── *.sh                    # Startup scripts
```

## 🔍 Troubleshooting

### Common Issues

1. **Port Occupied**
   ```bash
   # Check port usage
   lsof -i :8000
   lsof -i :3000
   
   # Stop occupying processes
   kill -9 <PID>
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis status
   redis-cli ping
   
   # Start Redis
   brew services start redis  # macOS
   systemctl start redis      # Linux
   ```

3. **Python Dependency Issues**
   ```bash
   # Reinstall dependencies
   pip install -r requirements.txt --force-reinstall
   ```

4. **Frontend Dependency Issues**
   ```bash
   # Clean and reinstall
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

### Log Viewing

```bash
# View all logs
tail -f logs/*.log

# View specific service logs
tail -f logs/backend.log
tail -f logs/frontend.log
tail -f logs/celery.log
```

### System Status Check

```bash
# Detailed status check
./status_autoclip.sh

# Manual service check
curl http://localhost:8000/api/v1/health/
curl http://localhost:3000/
redis-cli ping
```

## 🛠️ Development Mode

### Backend Development

```bash
# Activate virtual environment
source venv/bin/activate

# Set Python path
export PYTHONPATH="${PWD}:${PYTHONPATH}"

# Start backend (development mode)
python -m uvicorn backend.main:app --reload --port 8000
```

### Frontend Development

```bash
# Enter frontend directory
cd frontend

# Start development server
npm run dev
```

### Celery Worker

```bash
# Start Worker
celery -A backend.core.celery_app worker --loglevel=info

# Start Beat scheduler
celery -A backend.core.celery_app beat --loglevel=info

# Start Flower monitoring
celery -A backend.core.celery_app flower --port=5555
```

## 📈 Performance Optimization

### Production Environment Configuration

1. **Database Optimization**
   - Use PostgreSQL instead of SQLite
   - Configure connection pooling
   - Enable query caching

2. **Redis Optimization**
   - Configure memory limits
   - Enable persistence
   - Set expiration policies

3. **Celery Optimization**
   - Adjust concurrency
   - Configure task routing
   - Enable result backend

## 🔒 Security Configuration

### Production Environment Security

1. **Environment Variables**
   - Use strong passwords
   - Regularly rotate keys
   - Limit API access

2. **Network Security**
   - Configure firewall
   - Use HTTPS
   - Limit CORS

3. **Data Security**
   - Regular backups
   - Encrypt sensitive data
   - Access control

## 📞 Support

If you encounter problems, please:

1. View log files
2. Run status check script
3. Check environment configuration
4. Refer to the troubleshooting section

## 📄 License

This project is licensed under the MIT License.
