# 🔄 AI automatic clipping tool — project refactor plan

## 🎯 Refactoring strategy: progressive refactoring

### Why progressive refactoring?

**Advantages:**

- ✅ **Controlled risk** — Incremental changes instead of one big bang
- ✅ **Feature continuity** — Existing behavior stays available
- ✅ **Lower learning curve** — Team adapts gradually
- ✅ **Fast feedback** — Validate results at each stage
- ✅ **Easy rollback** — Revert quickly if something breaks

## 📋 Refactoring implementation plan

### Phase 1: Project restructuring (1 week)

#### Goal

Reorganize the project layout and lay groundwork for later refactors.

#### Steps

**1. Create new project structure**

```bash
# Run from project root
mkdir -p refactor-backup
cp -r * refactor-backup/  # Back up current project

# Create new directory layout
mkdir -p {backend,frontend,shared,docs,scripts,tests}
```

**2. Target layout**

```
autoclips-refactored/
├── backend/                    # Backend services
│   ├── app/                   # FastAPI application
│   ├── core/                  # Core modules
│   ├── services/              # Business services
│   ├── models/                # Data models
│   ├── api/                   # API routes
│   └── utils/                 # Utilities
├── frontend/                   # Frontend application
│   ├── src/                   # React source
│   ├── public/                # Static assets
│   └── dist/                  # Build output
├── shared/                     # Shared code
│   ├── types/                 # Type definitions
│   ├── constants/             # Constants
│   └── utils/                 # Shared utilities
├── docs/                       # Documentation
├── scripts/                    # Scripts
├── tests/                      # Tests
├── data/                       # Data files
├── logs/                       # Logs
└── requirements/               # Dependency manifests
```

**3. Migrate existing code**

```bash
# Migrate backend code
cp -r src/* backend/
cp -r pipeline backend/
cp -r utils backend/

# Migrate frontend code
cp -r frontend/* frontend/

# Migrate configuration
cp requirements.txt requirements/
cp backend_requirements.txt requirements/
```

**4. Remove redundant files**

```bash
# Remove duplicate API modules
rm -f src/api.py simple_api.py

# Remove experimental files
rm -f test_*.py
rm -f basic_bilibili_downloader.py
```

### Phase 2: Unified dependency management (3–5 days)

#### Goal

Centralize dependencies with modern package management.

#### Steps

**1. Create pyproject.toml**

```toml
[tool.poetry]
name = "auto-clips"
version = "1.0.0"
description = "AI automatic clipping tool"
authors = ["Your Name <your.email@example.com>"]

[tool.poetry.dependencies]
python = "^3.9"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.11.7"
dashscope = "^1.23.5"
pydub = "^0.25.1"
pysrt = "^1.1.2"
aiofiles = "^23.2.1"
python-multipart = "^0.0.6"
cryptography = "^42.0.5"
redis = "^5.0.1"
celery = "^5.3.4"
sqlalchemy = "^2.0.23"
psycopg2-binary = "^2.9.9"

[tool.poetry.dev-dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.21.1"
black = "^23.12.1"
isort = "^5.13.2"
mypy = "^1.8.0"
pre-commit = "^3.6.0"

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"
```

**2. Create package.json (frontend)**

```json
{
  "name": "auto-clips-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "antd": "^5.12.8",
    "axios": "^1.6.2",
    "zustand": "^4.4.7",
    "react-router-dom": "^6.20.1"
  },
  "devDependencies": {
    "@types/react": "^18.2.43",
    "@types/react-dom": "^18.2.17",
    "@vitejs/plugin-react": "^4.2.1",
    "typescript": "^5.2.2",
    "vite": "^5.0.8"
  }
}
```

**3. Install dependencies**

```bash
# Backend
cd backend
poetry install

# Frontend
cd ../frontend
npm install
```

### Phase 3: Backend architecture refactor (2–3 weeks)

#### Goal

Modernize backend structure and design patterns.

#### Steps

**1. New backend entry point**

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1 import projects, processing, files, settings
from app.core.config import settings as app_settings

app = FastAPI(
    title="AutoClips API",
    description="AI automatic clipping tool backend API",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(projects.router, prefix="/api/v1/projects", tags=["projects"])
app.include_router(processing.router, prefix="/api/v1/processing", tags=["processing"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])

@app.get("/")
async def root():
    return {"message": "AutoClips API", "version": "1.0.0"}
```

**2. Core configuration module**

```python
# backend/core/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # API configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AutoClips"
    
    # Security
    SECRET_KEY: str = "your-secret-key"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]
    
    # Database
    DATABASE_URL: str = "sqlite:///./autoclips.db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # File storage
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 1024 * 1024 * 100  # 100MB
    
    class Config:
        env_file = ".env"

settings = Settings()
```

**3. Service layer**

```python
# backend/services/project_service.py
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.core.exceptions import ProjectNotFoundError

class ProjectService:
    def __init__(self, db: Session):
        self.db = db
    
    def create_project(self, project_data: ProjectCreate) -> Project:
        project = Project(**project_data.dict())
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project
    
    def get_project(self, project_id: str) -> Optional[Project]:
        return self.db.query(Project).filter(Project.id == project_id).first()
    
    def get_projects(self, skip: int = 0, limit: int = 100) -> List[Project]:
        return self.db.query(Project).offset(skip).limit(limit).all()
    
    def update_project(self, project_id: str, project_data: ProjectUpdate) -> Project:
        project = self.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        
        for field, value in project_data.dict(exclude_unset=True).items():
            setattr(project, field, value)
        
        self.db.commit()
        self.db.refresh(project)
        return project
    
    def delete_project(self, project_id: str) -> bool:
        project = self.get_project(project_id)
        if not project:
            raise ProjectNotFoundError(project_id)
        
        self.db.delete(project)
        self.db.commit()
        return True
```

### Phase 4: Frontend architecture refactor (2–3 weeks)

#### Goal

Modernize the React frontend structure.

#### Steps

**1. Component structure**

```typescript
// frontend/src/components/layout/AppLayout.tsx
import React from 'react';
import { Layout, Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  HomeOutlined, 
  ProjectOutlined, 
  SettingOutlined,
  HistoryOutlined 
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;

interface AppLayoutProps {
  children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: 'Home',
    },
    {
      key: '/projects',
      icon: <ProjectOutlined />,
      label: 'Project Management',
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: 'Processing history',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
  };

  return (
    <Layout style={{ height: '100vh' }}>
      <Header className="app-header">
        <div className="logo">🎬 AutoClips</div>
      </Header>
      
      <Layout>
        <Sider width={200} theme="light">
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={handleMenuClick}
            style={{ height: '100%', borderRight: 0 }}
          />
        </Sider>
        
        <Layout style={{ padding: '24px' }}>
          <Content className="app-content">
            {children}
          </Content>
        </Layout>
      </Layout>
    </Layout>
  );
};
```

**2. State management**

```typescript
// frontend/src/store/projectStore.ts
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { Project, ProjectStatus } from '../types/project';
import { projectApi } from '../services/api';

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
  
  // Actions
  fetchProjects: () => Promise<void>;
  createProject: (projectData: Partial<Project>) => Promise<Project>;
  updateProject: (id: string, updates: Partial<Project>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
  startProcessing: (projectId: string) => Promise<void>;
}

export const useProjectStore = create<ProjectState>()(
  devtools(
    (set, get) => ({
      projects: [],
      currentProject: null,
      loading: false,
      error: null,

      fetchProjects: async () => {
        set({ loading: true, error: null });
        try {
          const projects = await projectApi.getProjects();
          set({ projects, loading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to fetch projects',
            loading: false 
          });
        }
      },

      createProject: async (projectData) => {
        set({ loading: true, error: null });
        try {
          const project = await projectApi.createProject(projectData);
          set(state => ({
            projects: [...state.projects, project],
            loading: false
          }));
          return project;
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to create project',
            loading: false 
          });
          throw error;
        }
      },

      updateProject: async (id, updates) => {
        set({ loading: true, error: null });
        try {
          await projectApi.updateProject(id, updates);
          set(state => ({
            projects: state.projects.map(p => 
              p.id === id ? { ...p, ...updates } : p
            ),
            loading: false
          }));
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to update project',
            loading: false 
          });
        }
      },

      deleteProject: async (id) => {
        set({ loading: true, error: null });
        try {
          await projectApi.deleteProject(id);
          set(state => ({
            projects: state.projects.filter(p => p.id !== id),
            loading: false
          }));
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to delete project',
            loading: false 
          });
        }
      },

      setCurrentProject: (project) => {
        set({ currentProject: project });
      },

      startProcessing: async (projectId) => {
        set({ loading: true, error: null });
        try {
          await projectApi.startProcessing(projectId);
          set({ loading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Failed to start processing',
            loading: false 
          });
        }
      },
    }),
    {
      name: 'project-store',
    }
  )
);
```

**3. API service**

```typescript
// frontend/src/services/api.ts
import axios, { AxiosInstance, AxiosResponse } from 'axios';
import { Project, ProcessingStatus } from '../types';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1',
      timeout: 300000, // 5 minutes
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response: AxiosResponse) => {
        return response.data;
      },
      (error) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  async getProjects(): Promise<Project[]> {
    return this.api.get('/projects');
  }

  async getProject(id: string): Promise<Project> {
    return this.api.get(`/projects/${id}`);
  }

  async createProject(projectData: Partial<Project>): Promise<Project> {
    return this.api.post('/projects', projectData);
  }

  async updateProject(id: string, updates: Partial<Project>): Promise<Project> {
    return this.api.put(`/projects/${id}`, updates);
  }

  async deleteProject(id: string): Promise<void> {
    return this.api.delete(`/projects/${id}`);
  }

  async startProcessing(projectId: string): Promise<void> {
    return this.api.post(`/projects/${projectId}/process`);
  }

  async getProcessingStatus(projectId: string): Promise<ProcessingStatus> {
    return this.api.get(`/projects/${projectId}/status`);
  }

  async uploadFiles(files: File[], projectId: string): Promise<void> {
    const formData = new FormData();
    files.forEach(file => {
      formData.append('files', file);
    });
    formData.append('project_id', projectId);

    return this.api.post('/files/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
  }
}

export const apiService = new ApiService();
```

### Phase 5: Database integration (1–2 weeks)

#### Goal

Add persistent storage with a proper data model.

#### Steps

**1. Database models**

```python
# backend/models/base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime
from datetime import datetime

Base = declarative_base()

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

```python
# backend/models/project.py
from sqlalchemy import Column, String, Text, JSON, Enum
from sqlalchemy.orm import relationship
from .base import Base, TimestampMixin
import enum

class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.CREATED)
    video_category = Column(String(50), default="default")
    metadata = Column(JSON)
    
    # Relationships
    clips = relationship("Clip", back_populates="project")
    collections = relationship("Collection", back_populates="project")
```

**2. Database configuration**

```python
# backend/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Phase 6: Testing and optimization (1–2 weeks)

#### Goal

Increase test coverage and optimize performance.

#### Steps

**1. Unit tests**

```python
# tests/test_project_service.py
import pytest
from unittest.mock import Mock
from app.services.project_service import ProjectService
from app.models.project import Project
from app.schemas.project import ProjectCreate

class TestProjectService:
    @pytest.fixture
    def mock_db(self):
        return Mock()
    
    @pytest.fixture
    def project_service(self, mock_db):
        return ProjectService(mock_db)
    
    def test_create_project(self, project_service, mock_db):
        # Arrange
        project_data = ProjectCreate(
            name="Test project",
            description="This is a test project"
        )
        mock_project = Project(
            id="test-id",
            name=project_data.name,
            description=project_data.description
        )
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # Act
        result = project_service.create_project(project_data)
        
        # Assert
        assert result.name == project_data.name
        assert result.description == project_data.description
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
```

**2. Integration tests**

```python
# tests/test_api.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_project():
    response = client.post(
        "/api/v1/projects/",
        json={
            "name": "Test project",
            "description": "This is a test project"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test project"
```

## 🔧 Refactoring tools and scripts

### 1. Refactor helper script

```bash
#!/bin/bash
# scripts/refactor.sh

echo "🔄 Starting project refactor..."

# Back up current project
echo "📦 Backing up current project..."
mkdir -p backup/$(date +%Y%m%d_%H%M%S)
cp -r * backup/$(date +%Y%m%d_%H%M%S)/

# Create new directory structure
echo "📁 Creating new directory structure..."
mkdir -p {backend,frontend,shared,docs,scripts,tests}

# Migrate code
echo "📋 Migrating existing code..."
cp -r src/* backend/
cp -r pipeline backend/
cp -r utils backend/
cp -r frontend/* frontend/

# Clean up redundant files
echo "🧹 Cleaning up redundant files..."
rm -f src/api.py simple_api.py
rm -f test_*.py
rm -f basic_bilibili_downloader.py

echo "✅ Refactor complete!"
```

### 2. Development environment script

```bash
#!/bin/bash
# scripts/dev.sh

echo "🚀 Starting development environment..."

# Check dependencies
if ! command -v poetry &> /dev/null; then
    echo "❌ Poetry is not installed; install Poetry first"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed; install Node.js first"
    exit 1
fi

# Install backend dependencies
echo "📦 Installing backend dependencies..."
cd backend
poetry install
cd ..

# Install frontend dependencies
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Start backend
echo "🔧 Starting backend..."
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "✅ Development environment started!"
echo "📱 Frontend: http://localhost:3000"
echo "🔌 Backend API: http://localhost:8000"
echo "📚 API docs: http://localhost:8000/docs"

trap 'echo "\n🛑 Stopping services..."; kill $BACKEND_PID $FRONTEND_PID; exit' INT
wait
```

## 📊 Refactoring checklist

### Phase 1

- [ ] Project structure reorganized
- [ ] Redundant files removed
- [ ] Code migrated
- [ ] Basic functionality verified

### Phase 2

- [ ] Poetry configuration complete
- [ ] Dependencies installed
- [ ] Package management unified
- [ ] Development environment works

### Phase 3

- [ ] Backend architecture refactored
- [ ] API redesigned
- [ ] Service layer refactored
- [ ] Error handling improved

### Phase 4

- [ ] Frontend architecture refactored
- [ ] Components redesigned
- [ ] State management optimized
- [ ] API client refactored

### Phase 5

- [ ] Database models designed
- [ ] Migrations applied
- [ ] Persistence working
- [ ] Performance optimized

### Phase 6

- [ ] Unit test coverage
- [ ] Integration tests complete
- [ ] Performance tests passing
- [ ] Documentation updated

## 🎯 Refactoring benefits

### Technical

1. **Clear architecture** — Modular design, separation of concerns
2. **Code quality** — Modern development practices
3. **Maintainability** — Easier to understand and change
4. **Scalability** — Room for new features

### Development

1. **Velocity** — Better developer experience
2. **Debugging** — Clearer error messages
3. **Testing** — Solid test foundation
4. **Deployment** — Standardized process

### User experience

1. **Responsiveness** — Better performance
2. **Stability** — More reliable system
3. **Features** — Richer product experience
4. **Errors** — Friendly error messages

---

## 🚀 Getting started

1. **Back up the project** — Protect current code
2. **Create a branch** — Use a dedicated Git branch
3. **Execute phase by phase** — Follow the plan in order
4. **Test continuously** — Validate at each stage
5. **Commit regularly** — Small, frequent commits

This progressive refactor keeps the project stable while improving code quality and architecture over time.
