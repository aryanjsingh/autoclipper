# 🚀 AI Slicing Project Refactoring — Quick Start Guide

## 📋 Project Introduction

The AI slicing tool is an AI-based automatic video clipping tool that cuts long videos into multiple highlight clips. This project is being refactored to establish a modern backend architecture.

## 🎯 Refactoring Goals

1. **Data persistence**: Introduce SQLite + SQLAlchemy for data management  
2. **Service modularization**: Refactor FastAPI into modular service management  
3. **Task scheduling**: Connect frontend and backend task scheduling systems  

## 🏗️ Project Structure

```
autoclip/
├── backend/                    # Backend services
│   ├── app/                   # FastAPI application
│   ├── api/                   # API routes
│   ├── core/                  # Core modules
│   ├── models/                # Data models
│   ├── services/              # Business services
│   └── tasks/                 # Task queue
├── frontend/                   # Frontend application
├── shared/                     # Shared code
├── docs/                       # Documentation
└── data/                       # Data files
```

## 🛠️ Development Environment Setup

### Required Tools
- Python 3.9+
- Node.js 16+
- Redis
- Git

### Installation Steps

1. **Clone the project**
```bash
git clone <repository-url>
cd autoclip
```

2. **Backend environment**
```bash
cd backend
# Install Poetry (if not installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Activate virtual environment
poetry shell
```

3. **Frontend environment**
```bash
cd frontend
npm install
```

4. **Start Redis**
```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt-get install redis-server
sudo systemctl start redis
```

## 🚀 Quick Start

### 1. Start the backend service
```bash
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Start the frontend service
```bash
cd frontend
npm run dev
```

### 3. Access the application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs

## 📚 Development Guide

### Backend Development

#### Add a new API route
1. Create a new route file under `backend/api/v1/`
2. Register routes in `backend/app/main.py`
3. Implement service logic under `backend/services/`

```python
# backend/api/v1/example.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.core.database import get_db
from backend.services.example_service import ExampleService

router = APIRouter()

@router.get("/example")
async def get_example(db: Session = Depends(get_db)):
    service = ExampleService(db)
    return service.get_examples()
```

#### Add a new data model
1. Create model files under `backend/models/`
2. Inherit from `Base` and add required fields
3. Run database migration

```python
# backend/models/example.py
from sqlalchemy import Column, String, DateTime
from backend.models.base import Base, TimestampMixin

class Example(Base, TimestampMixin):
    __tablename__ = "examples"
    
    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500))
```

#### Add a new service
1. Create service files under `backend/services/`
2. Implement business logic
3. Add error handling and logging

```python
# backend/services/example_service.py
from sqlalchemy.orm import Session
from backend.models.example import Example
from backend.schemas.example import ExampleCreate

class ExampleService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_example(self, example_data: ExampleCreate) -> Example:
        example = Example(**example_data.dict())
        self.db.add(example)
        self.db.commit()
        self.db.refresh(example)
        return example
```

### Frontend Development

#### Add a new page
1. Create page components under `frontend/src/pages/`
2. Add routes in the router configuration
3. Add navigation menu links

```typescript
// frontend/src/pages/ExamplePage.tsx
import React from 'react';
import { Card, Table } from 'antd';

const ExamplePage: React.FC = () => {
  return (
    <Card title="Example Page">
      <Table />
    </Card>
  );
};

export default ExamplePage;
```

#### Add a new API call
1. Add API methods under `frontend/src/services/`
2. Call APIs from components
3. Add error handling and loading states

```typescript
// frontend/src/services/api.ts
export const exampleApi = {
  getExamples: async (): Promise<Example[]> => {
    const response = await apiService.get('/examples');
    return response.data;
  },
  
  createExample: async (data: ExampleCreate): Promise<Example> => {
    const response = await apiService.post('/examples', data);
    return response.data;
  }
};
```

## 🧪 Testing Guide

### Run backend tests
```bash
cd backend
poetry run pytest
```

### Run frontend tests
```bash
cd frontend
npm test
```

### Run end-to-end tests
```bash
# Start all services
npm run test:e2e
```

## 📊 Database Operations

### Create a migration
```bash
cd backend
alembic revision --autogenerate -m "describe change"
```

### Apply migrations
```bash
alembic upgrade head
```

### Roll back a migration
```bash
alembic downgrade -1
```

## 🔧 Common Commands

### Development
```bash
# Start backend dev server
poetry run uvicorn app.main:app --reload

# Start frontend dev server
npm run dev

# Build frontend
npm run build

# Run tests
poetry run pytest
npm test
```

### Database
```bash
# Create migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head

# View migration history
alembic history
```

### Deployment
```bash
# Build Docker image
docker build -t autoclip .

# Run Docker container
docker run -p 8000:8000 autoclip
```

## 🐛 FAQ

### 1. Database connection failed
**Problem**: Cannot connect to the database  
**Solution**:
- Check that the database file exists
- Verify database permissions
- Check the database connection string

### 2. Redis connection failed
**Problem**: Celery cannot connect to Redis  
**Solution**:
- Confirm Redis is running
- Check Redis connection configuration
- Confirm the Redis port is not in use

### 3. Frontend build failed
**Problem**: `npm run build` failed  
**Solution**:
- Remove `node_modules` and reinstall
- Check for TypeScript type errors
- Ensure all dependencies are installed

### 4. API call failed
**Problem**: Frontend cannot call the backend API  
**Solution**:
- Confirm the backend service is running
- Check CORS configuration
- Verify API endpoint paths

## 📞 Getting Help

### Documentation
- [Refactoring Implementation Plan](./REFACTOR_IMPLEMENTATION_PLAN.md)
- [Work Item Breakdown](./WORK_ITEMS_BREAKDOWN.md)
- [Project Management](./PROJECT_MANAGEMENT.md)

### Technology stack
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [React Documentation](https://reactjs.org/docs/)

### Feedback
- Create a GitHub Issue
- Contact the project maintainer
- See the project wiki

## 🎉 Next Steps

1. **Learn the project structure**: Read code and documentation  
2. **Set up the dev environment**: Follow the steps above  
3. **Run the example**: Start services and test functionality  
4. **Start development**: Pick a work item and begin  
5. **Submit code**: Follow project coding standards  

---

**Document version**: 1.0  
**Created**: December 2024  
**Last updated**: December 2024
