# Docker Deployment Guide

This document describes how to deploy the AutoClip system using Docker.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Production Environment Deployment](#production-environment-deployment)
- [Development Environment Deployment](#development-environment-deployment)
- [Configuration](#configuration)
- [Data Management](#data-management)
- [Troubleshooting](#troubleshooting)

## 🚀 Quick Start

### Requirements

- Docker 20.10+
- Docker Compose 2.0+
- At least 4GB available memory
- At least 10GB available disk space

### One-Click Startup

```bash
# Clone the project
git clone https://github.com/your-username/autoclip.git
cd autoclip

# Configure environment variables
cp env.example .env
# Edit .env file and fill in necessary configurations

# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### Access Services

- **Frontend Interface**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Flower Monitoring**: http://localhost:5555

## 🏭 Production Environment Deployment

### Using Production Configuration

```bash
# Use production environment configuration
docker-compose -f docker-compose.yml up -d

# Run in background
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f autoclip
```

### Production Environment Optimization

1. **Resource Limits**
```yaml
# Add resource limits in docker-compose.yml
services:
  autoclip:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

2. **Data Persistence**
```bash
# Create data volumes
docker volume create autoclip_data
docker volume create autoclip_logs

# Configure in docker-compose.yml
volumes:
  - autoclip_data:/app/data
  - autoclip_logs:/app/logs
```

3. **Network Configuration**
```yaml
# Use custom network
networks:
  autoclip-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 🛠️ Development Environment Deployment

### Using Development Configuration

```bash
# Use development environment configuration
docker-compose -f docker-compose.dev.yml up -d

# View logs in real-time
docker-compose -f docker-compose.dev.yml logs -f

# Enter container for debugging
docker-compose -f docker-compose.dev.yml exec autoclip-dev bash
```

### Development Environment Features

- Hot reload support
- Debug mode
- Detailed logging
- Code mounting

## ⚙️ Configuration

### Environment Variables

Create `.env` file:

```bash
# Database configuration
DATABASE_URL=sqlite:///./data/autoclip.db

# Redis configuration
REDIS_URL=redis://redis:6379/0

# API configuration
API_DASHSCOPE_API_KEY=your_dashscope_api_key
API_MODEL_NAME=qwen-plus

# Logging configuration
LOG_LEVEL=INFO
ENVIRONMENT=production
DEBUG=false

# File storage
UPLOAD_DIR=./data/uploads
PROJECT_DIR=./data/projects
```

### Service Configuration

#### Main Application Service
- **Ports**: 8000 (backend), 3000 (frontend)
- **Health Check**: `/api/v1/health/`
- **Restart Policy**: `unless-stopped`

#### Redis Service
- **Port**: 6379
- **Persistence**: AOF mode
- **Memory Limit**: Configurable

#### Celery Service
- **Worker**: Process asynchronous tasks
- **Beat**: Scheduled task scheduling
- **Concurrency**: Configurable

## 💾 Data Management

### Data Persistence

```bash
# View data volumes
docker volume ls

# Backup data
docker run --rm -v autoclip_data:/data -v $(pwd):/backup alpine tar czf /backup/autoclip-backup.tar.gz -C /data .

# Restore data
docker run --rm -v autoclip_data:/data -v $(pwd):/backup alpine tar xzf /backup/autoclip-backup.tar.gz -C /data
```

### Data Directory Structure

```
data/
├── autoclip.db          # SQLite database
├── projects/            # Project data
├── uploads/             # Uploaded files
├── temp/                # Temporary files
└── output/              # Output files
```

### Clean Up Data

```bash
# Clean temporary files
docker-compose exec autoclip find /app/data/temp -type f -mtime +7 -delete

# Clean logs
docker-compose exec autoclip find /app/logs -name "*.log" -mtime +30 -delete
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Service Startup Failure

```bash
# Check service status
docker-compose ps

# View detailed logs
docker-compose logs autoclip

# Restart service
docker-compose restart autoclip
```

#### 2. Port Conflict

```bash
# Check port usage
netstat -tulpn | grep :8000

# Modify port mapping
# Modify ports configuration in docker-compose.yml
ports:
  - "8001:8000"  # Map local port 8001 to container port 8000
```

#### 3. Insufficient Memory

```bash
# View container resource usage
docker stats

# Limit resource usage
# Add deploy configuration in docker-compose.yml
```

#### 4. Data Loss

```bash
# Check data volume
docker volume inspect autoclip_data

# Restore backup
# Use the backup restore commands above
```

### Log Viewing

```bash
# View all service logs
docker-compose logs

# View specific service logs
docker-compose logs autoclip
docker-compose logs celery-worker

# View logs in real-time
docker-compose logs -f

# View last 100 lines of logs
docker-compose logs --tail=100
```

### Performance Monitoring

```bash
# View container resource usage
docker stats

# Check service health status
docker-compose ps

# Enter container for debugging
docker-compose exec autoclip bash
```

## 🔄 Updates and Maintenance

### Update Services

```bash
# Pull latest code
git pull

# Rebuild images
docker-compose build

# Restart services
docker-compose up -d
```

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Automatic backup script

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/autoclip"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup data
docker run --rm -v autoclip_data:/data -v $BACKUP_DIR:/backup alpine \
    tar czf /backup/autoclip-data-$DATE.tar.gz -C /data .

# Backup configuration
cp .env $BACKUP_DIR/autoclip-config-$DATE.env

# Clean old backups (keep 7 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
find $BACKUP_DIR -name "*.env" -mtime +7 -delete

echo "Backup completed: $DATE"
```

### Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Service monitoring script

# Check service status
if ! docker-compose ps | grep -q "Up"; then
    echo "Service abnormal, attempting restart..."
    docker-compose restart
fi

# Check health status
if ! curl -f http://localhost:8000/api/v1/health/ >/dev/null 2>&1; then
    echo "Health check failed, sending alert..."
    # Add alert logic here
fi
```

## 📚 Advanced Configuration

### Using External Database

```yaml
# Use PostgreSQL
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: autoclip
      POSTGRES_USER: autoclip
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  autoclip:
    environment:
      - DATABASE_URL=postgresql://autoclip:password@postgres:5432/autoclip
    depends_on:
      - postgres
```

### Using External Redis

```yaml
# Use external Redis cluster
services:
  autoclip:
    environment:
      - REDIS_URL=redis://redis-cluster:6379/0
    external_links:
      - redis-cluster:redis
```

### Load Balancing

```yaml
# Use Nginx load balancing
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - autoclip

  autoclip:
    # Can start multiple instances
    scale: 3
```

## 🆘 Getting Help

If you encounter problems, please:

1. Check the troubleshooting section of this document
2. Check GitHub Issues
3. View project documentation
4. Contact technical support

---

**Last Updated**: 2024-01-15
