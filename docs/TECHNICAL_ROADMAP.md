# 🎬 AI automatic clipping tool — technical evolution roadmap

## 📋 Current state analysis

### Architecture today

1. **Dual frontend**: Streamlit prototype + React production UI
2. **Multiple backend services**: FastAPI main service + several API modules
3. **6-step pipeline**: Outline extraction through video cutting
4. **Multi-project support**: Separate data directories and configuration per project

### Key problems

#### 1. **Redundant and fragmented architecture**

- Duplicate API entry points (`backend_server.py`, `src/api.py`, `simple_api.py`)
- Streamlit and React dual frontend increases maintenance cost
- No unified service entry or routing

#### 2. **Technical debt**

- Split dependency management (`requirements.txt`, `backend_requirements.txt`)
- Incomplete error handling and monitoring
- Unclear module boundaries and high coupling

#### 3. **Performance and scalability**

- No caching or database layer
- Simple file storage; limited large-file support
- Limited concurrency

#### 4. **User experience**

- Weak progress feedback and error recovery
- Configuration UX needs improvement
- Incomplete logging and observability

## 🚀 Phased technical evolution

### Phase 1: Architecture cleanup and foundation (2–3 weeks)

#### Goals

Remove redundancy, establish a clear architecture, and prepare for later phases.

#### Tasks

**1. Backend refactor**

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry
│   ├── config.py            # Unified configuration
│   ├── dependencies.py      # Dependency injection
│   └── middleware.py        # Middleware
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── projects.py      # Project APIs
│   │   ├── processing.py    # Processing APIs
│   │   ├── files.py         # File upload APIs
│   │   └── settings.py      # Settings APIs
│   └── deps.py              # API dependencies
├── core/
│   ├── __init__.py
│   ├── config.py            # Core configuration
│   ├── security.py          # Security
│   └── exceptions.py        # Exception handling
├── models/
│   ├── __init__.py
│   ├── project.py           # Project model
│   ├── clip.py              # Clip model
│   └── collection.py        # Collection model
├── services/
│   ├── __init__.py
│   ├── project_service.py   # Project service
│   ├── processing_service.py # Processing service
│   ├── file_service.py      # File service
│   └── llm_service.py       # LLM service
├── pipeline/
│   ├── __init__.py
│   ├── base.py              # Pipeline base class
│   ├── steps/               # Processing steps
│   └── orchestrator.py      # Pipeline orchestration
└── utils/
    ├── __init__.py
    ├── file_utils.py        # File utilities
    ├── video_utils.py       # Video utilities
    └── text_utils.py        # Text utilities
```

**2. Frontend optimization**

```
frontend/
├── src/
│   ├── components/
│   │   ├── common/          # Shared components
│   │   ├── forms/           # Form components
│   │   ├── layout/          # Layout components
│   │   └── features/        # Feature components
│   ├── hooks/
│   │   ├── useApi.ts        # API hook
│   │   ├── useProject.ts    # Project hook
│   │   └── useProcessing.ts # Processing status hook
│   ├── services/
│   │   ├── api.ts           # API client
│   │   ├── project.ts       # Project service
│   │   └── processing.ts    # Processing service
│   ├── store/
│   │   ├── index.ts         # Store entry
│   │   ├── project.ts       # Project state
│   │   └── settings.ts      # Settings state
│   ├── types/
│   │   ├── api.ts           # API types
│   │   ├── project.ts       # Project types
│   │   └── common.ts        # Shared types
│   └── utils/
│       ├── constants.ts     # Constants
│       ├── helpers.ts       # Helpers
│       └── validation.ts    # Validation
```

**3. Unified dependency management**

```toml
# pyproject.toml — unified Python dependencies
[tool.poetry]
name = "auto-clip"
version = "1.0.0"
description = "AI automatic clipping tool"

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

[tool.poetry.dev-dependencies]
pytest = "^8.0.0"
pytest-asyncio = "^0.21.1"
black = "^23.12.1"
isort = "^5.13.2"
mypy = "^1.8.0"
```

### Phase 2: Core capability enhancements (3–4 weeks)

#### Goals

Strengthen processing, improve UX, and increase stability.

#### Tasks

**1. Database integration**

```python
# SQLAlchemy + PostgreSQL
from sqlalchemy import create_engine, Column, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Project(Base):
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    status = Column(String, default="created")
    video_category = Column(String, default="default")
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**2. Caching**

```python
# Redis cache integration
import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache_result(expire_time=3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            cached_result = redis_client.get(cache_key)
            
            if cached_result:
                return json.loads(cached_result)
            
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, expire_time, json.dumps(result))
            return result
        return wrapper
    return decorator
```

**3. Async task queue**

```python
# Celery task queue
from celery import Celery
from celery.utils.log import get_task_logger

celery_app = Celery('auto_clips', broker='redis://localhost:6379/1')

@celery_app.task(bind=True)
def process_video_pipeline(self, project_id: str, start_step: int = 1):
    """Process video pipeline asynchronously"""
    try:
        processor = AutoClipsProcessor(project_id)
        
        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={'current_step': start_step, 'total_steps': 6}
        )
        
        if start_step == 1:
            result = processor.run_full_pipeline()
        else:
            result = processor.run_from_step(start_step)
            
        return {'status': 'SUCCESS', 'result': result}
    except Exception as e:
        return {'status': 'FAILURE', 'error': str(e)}
```

**4. File storage optimization**

```python
# Multiple storage backends
from abc import ABC, abstractmethod
import boto3
from pathlib import Path

class StorageBackend(ABC):
    @abstractmethod
    async def upload_file(self, file_path: Path, destination: str) -> str:
        pass
    
    @abstractmethod
    async def download_file(self, source: str, destination: Path) -> None:
        pass

class LocalStorageBackend(StorageBackend):
    async def upload_file(self, file_path: Path, destination: str) -> str:
        # Local storage logic
        pass

class S3StorageBackend(StorageBackend):
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client('s3')
        self.bucket_name = bucket_name
    
    async def upload_file(self, file_path: Path, destination: str) -> str:
        # S3 upload logic
        pass
```

### Phase 3: Performance and observability (2–3 weeks)

#### Goals

Improve performance and establish monitoring and logging.

#### Tasks

**1. Performance monitoring**

```python
# Prometheus + Grafana
from prometheus_client import Counter, Histogram, Gauge
import time

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_PROCESSING = Gauge('active_processing_tasks', 'Number of active processing tasks')

@app.middleware("http")
async def monitor_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response
```

**2. Logging**

```python
# Structured logging
import structlog
from structlog.stdlib import LoggerFactory

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()
```

**3. Enhanced error handling**

```python
# Global error handling
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=request.url.path,
        method=request.method
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": request.headers.get("X-Request-ID", "unknown")
        }
    )
```

### Phase 4: User experience (2–3 weeks)

#### Goals

Improve UI/UX and streamline workflows.

#### Tasks

**1. Real-time progress**

```typescript
// WebSocket real-time updates
import { io, Socket } from 'socket.io-client';

class ProcessingSocket {
  private socket: Socket;
  
  constructor(projectId: string) {
    this.socket = io('ws://localhost:8000', {
      query: { project_id: projectId }
    });
    
    this.socket.on('processing_progress', (data) => {
      this.updateProgress(data);
    });
    
    this.socket.on('processing_complete', (data) => {
      this.handleComplete(data);
    });
  }
  
  private updateProgress(data: ProcessingProgress) {
    // Update progress UI
  }
}
```

**2. Drag-and-drop upload**

```typescript
// Enhanced file upload
import { useDropzone } from 'react-dropzone';

const FileUploadZone = () => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'video/*': ['.mp4', '.avi', '.mov', '.mkv'],
      'text/plain': ['.srt']
    },
    multiple: true,
    onDrop: handleFileDrop
  });
  
  return (
    <div {...getRootProps()} className={isDragActive ? 'drag-active' : ''}>
      <input {...getInputProps()} />
      {isDragActive ? (
        <p>Drop files here...</p>
      ) : (
        <p>Click or drag files here to upload</p>
      )}
    </div>
  );
};
```

**3. Configuration wizard**

```typescript
// Configuration wizard
const ConfigurationWizard = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [config, setConfig] = useState({});
  
  const steps = [
    {
      title: 'API configuration',
      component: <ApiConfigStep config={config} onChange={setConfig} />
    },
    {
      title: 'Processing parameters',
      component: <ProcessingConfigStep config={config} onChange={setConfig} />
    },
    {
      title: 'Storage settings',
      component: <StorageConfigStep config={config} onChange={setConfig} />
    }
  ];
  
  return (
    <div className="config-wizard">
      <Steps current={currentStep} items={steps} />
      {steps[currentStep - 1].component}
    </div>
  );
};
```

## 🛠️ Technology stack

### Backend

**Core**

- **FastAPI**: High-performance async web framework with OpenAPI docs
- **SQLAlchemy**: ORM for multiple databases
- **Pydantic**: Validation and serialization
- **Celery**: Distributed task queue

**Storage**

- **PostgreSQL**: Primary database with JSON support
- **Redis**: Cache and sessions
- **MinIO/S3**: Object storage for large files

**Observability**

- **Prometheus**: Metrics
- **Grafana**: Dashboards
- **ELK Stack**: Log analysis

### Frontend

**Core**

- **React 18**: UI framework
- **TypeScript**: Type safety
- **Vite**: Build tool

**State**

- **Zustand**: Lightweight client state
- **React Query**: Server state

**UI**

- **Ant Design**: Component library
- **Tailwind CSS**: Utility-first CSS

**Real-time**

- **Socket.IO**: WebSocket client/server
- **Server-Sent Events**: One-way streams

### Deployment and operations

**Containers**

- **Docker**: Application containers
- **Docker Compose**: Multi-service orchestration

**CI/CD**

- **GitHub Actions**: Automation
- **ArgoCD**: GitOps deployments

**Monitoring**

- **Prometheus**: Metrics
- **Grafana**: Visualization
- **Jaeger**: Distributed tracing

## 📅 Timeline

```
Weeks 1–2: Architecture cleanup
├── Backend refactor
├── Frontend optimization
└── Unified dependencies

Weeks 3–5: Core enhancements
├── Database integration
├── Caching
├── Async task queue
└── File storage optimization

Weeks 6–7: Performance and observability
├── Performance monitoring
├── Logging
└── Error handling

Weeks 8–9: User experience
├── Real-time progress
├── Drag-and-drop upload
└── Configuration wizard

Week 10: Test and deploy
├── Integration tests
├── Performance tests
└── Production deployment
```

## 🎯 Expected outcomes

### Technical

1. **Clear architecture**: Modular, maintainable, extensible
2. **Better performance**: Caching and async processing
3. **Higher stability**: Error handling and monitoring
4. **Scalability**: Horizontal scaling and microservices path

### User experience

1. **Simpler workflows**: Intuitive UI and guided configuration
2. **Real-time feedback**: Live processing progress
3. **Error recovery**: Smarter failure handling
4. **Responsive UI**: Fast, smooth interactions

## 📋 Risk assessment

### Technical risks

1. **Migration risk**: Refactor may affect existing behavior
   - **Mitigation**: Progressive refactor; maintain backwards compatibility

2. **Performance risk**: New architecture may introduce bottlenecks
   - **Mitigation**: Baselines, continuous monitoring, optimization

3. **Dependency risk**: New packages may cause compatibility issues
   - **Mitigation**: Thorough testing; rollback plan

### Project risks

1. **Schedule risk**: Timeline may slip
   - **Mitigation**: Milestone reviews; adjust scope

2. **Resource risk**: Insufficient development capacity
   - **Mitigation**: Prioritize core features; phased delivery

## 🔄 Continuous improvement

### Short term (1–3 months)

- Collect and analyze user feedback
- Performance tuning and bug fixes
- Feature polish and UX improvements

### Medium term (3–6 months)

- New features and integrations
- Further architecture optimization
- Scalability and reliability improvements

### Long term (6–12 months)

- Microservices migration
- Enhanced AI capabilities
- Commercial feature development

---

*This document guides technical evolution. Update it regularly based on progress and user feedback.*
