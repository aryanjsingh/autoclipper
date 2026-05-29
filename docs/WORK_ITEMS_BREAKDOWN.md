# 📋 AI clipping project refactor work breakdown

## 🎯 Overall goal

Refactor the AI clipping project into a modern architecture with persistent storage, modular services, and real-time task scheduling.

## 📅 Phase 1: Persistent data storage (1 week)

### Work item 1.1: Database model design (2 days)

#### Task 1.1.1: Base model design (0.5 day)

- [ ] Create `backend/models/base.py`
  - [ ] Define `Base` inheriting from `declarative_base()`
  - [ ] Create `TimestampMixin` mixin
  - [ ] Implement `created_at` and `updated_at` fields
  - [ ] Add UUID generation logic for `id`

#### Task 1.1.2: Project model design (0.5 day)

- [ ] Create `backend/models/project.py`
  - [ ] Define `Project` model
  - [ ] Implement `ProjectStatus` enum
  - [ ] Add basic project fields
  - [ ] Define relationships to clips and collections

#### Task 1.1.3: Clip model design (0.5 day)

- [ ] Create `backend/models/clip.py`
  - [ ] Define `Clip` model
  - [ ] Implement `ClipStatus` enum
  - [ ] Add clip metadata fields
  - [ ] Define relationships to projects and collections

#### Task 1.1.4: Collection model design (0.5 day)

- [ ] Create `backend/models/collection.py`
  - [ ] Define `Collection` model
  - [ ] Implement `CollectionStatus` enum
  - [ ] Add collection metadata fields
  - [ ] Define relationships to projects and clips

### Work item 1.2: SQLAlchemy integration (2 days)

#### Task 1.2.1: Database configuration (0.5 day)

- [ ] Create `backend/core/database.py`
  - [ ] Configure SQLite connection
  - [ ] Create engine (`create_engine`)
  - [ ] Configure session factory (`SessionLocal`)
  - [ ] Implement database dependency injection

#### Task 1.2.2: Alembic migration setup (0.5 day)

- [ ] Install and configure Alembic
- [ ] Create `alembic.ini`
- [ ] Initialize migration environment
- [ ] Create initial migration script

#### Task 1.2.3: Database initialization (0.5 day)

- [ ] Create database initialization script
- [ ] Implement table creation logic
- [ ] Add connection tests
- [ ] Add database reset capability

#### Task 1.2.4: Data migration tooling (0.5 day)

- [ ] Create migration script for existing data
- [ ] Implement JSON-to-database conversion
- [ ] Add data validation
- [ ] Add migration rollback

### Work item 1.3: Data access layer (1 day)

#### Task 1.3.1: Repository pattern (0.5 day)

- [ ] Create `backend/repositories/` directory
- [ ] Implement base repository class
- [ ] Create project repository
- [ ] Create clip repository
- [ ] Create collection repository

#### Task 1.3.2: CRUD operations (0.5 day)

- [ ] Implement project CRUD
- [ ] Implement clip CRUD
- [ ] Implement collection CRUD
- [ ] Add validation and constraint checks

## 📅 Phase 2: FastAPI service modularization (2 weeks)

### Work item 2.1: API route refactor (3 days)

#### Task 2.1.1: API dependencies (0.5 day)

- [ ] Create `backend/api/deps.py`
  - [ ] Database session dependency
  - [ ] Authentication dependency (future)
  - [ ] Error handling dependency
  - [ ] Logging dependency

#### Task 2.1.2: Project API routes (0.5 day)

- [ ] Create `backend/api/v1/projects.py`
  - [ ] `POST /projects` — create project
  - [ ] `GET /projects` — list projects
  - [ ] `GET /projects/{id}` — project details
  - [ ] `PUT /projects/{id}` — update project
  - [ ] `DELETE /projects/{id}` — delete project

#### Task 2.1.3: Processing API routes (0.5 day)

- [ ] Create `backend/api/v1/processing.py`
  - [ ] `POST /processing/start` — start task
  - [ ] `GET /processing/{id}/status` — task status
  - [ ] `POST /processing/{id}/cancel` — cancel task
  - [ ] `GET /processing` — list tasks

#### Task 2.1.4: File upload API routes (0.5 day)

- [ ] Create `backend/api/v1/files.py`
  - [ ] `POST /files/upload` — upload file
  - [ ] `GET /files` — list files
  - [ ] `DELETE /files/{id}` — delete file
  - [ ] File type and size validation

#### Task 2.1.5: Clip management API routes (0.5 day)

- [ ] Create `backend/api/v1/clips.py`
  - [ ] `GET /clips` — list clips
  - [ ] `GET /clips/{id}` — clip details
  - [ ] `PUT /clips/{id}` — update clip
  - [ ] `DELETE /clips/{id}` — delete clip

#### Task 2.1.6: Collection management API routes (0.5 day)

- [ ] Create `backend/api/v1/collections.py`
  - [ ] `POST /collections` — create collection
  - [ ] `GET /collections` — list collections
  - [ ] `GET /collections/{id}` — collection details
  - [ ] `PUT /collections/{id}` — update collection
  - [ ] `DELETE /collections/{id}` — delete collection

### Work item 2.2: Service layer refactor (3 days)

#### Task 2.2.1: Project service (0.5 day)

- [ ] Create `backend/services/project_service.py`
  - [ ] Create project logic
  - [ ] Query project logic
  - [ ] Update project logic
  - [ ] Delete project logic
  - [ ] Business rule validation

#### Task 2.2.2: Processing service (1 day)

- [ ] Create `backend/services/processing_service.py`
  - [ ] Integrate existing 6-step pipeline
  - [ ] Task creation logic
  - [ ] Processing state management
  - [ ] Result persistence
  - [ ] Error handling and retries

#### Task 2.2.3: File service (0.5 day)

- [ ] Create `backend/services/file_service.py`
  - [ ] Upload logic
  - [ ] Storage management
  - [ ] File validation
  - [ ] Cleanup mechanism

#### Task 2.2.4: Clip service (0.5 day)

- [ ] Create `backend/services/clip_service.py`
  - [ ] Create clip logic
  - [ ] Query clip logic
  - [ ] Update clip logic
  - [ ] Delete clip logic

#### Task 2.2.5: Collection service (0.5 day)

- [ ] Create `backend/services/collection_service.py`
  - [ ] Create collection logic
  - [ ] Query collection logic
  - [ ] Update collection logic
  - [ ] Delete collection logic

### Work item 2.3: Middleware and dependency injection (2 days)

#### Task 2.3.1: Error handling middleware (0.5 day)

- [ ] Create `backend/app/middleware.py`
  - [ ] Global exception handling
  - [ ] Custom exception classes
  - [ ] Error response formatting
  - [ ] Error logging

#### Task 2.3.2: CORS middleware (0.5 day)

- [ ] Configure CORS middleware
- [ ] Allowed origins and methods
- [ ] Auth header support
- [ ] Preflight handling

#### Task 2.3.3: Logging middleware (0.5 day)

- [ ] Request logging
- [ ] Response time metrics
- [ ] Structured log format
- [ ] Log level configuration

#### Task 2.3.4: Auth middleware (future) (0.5 day)

- [ ] Auth middleware framework
- [ ] JWT validation
- [ ] Permission checks
- [ ] Session management

### Work item 2.4: Testing and debugging (2 days)

#### Task 2.4.1: Unit tests (1 day)

- [ ] Service layer unit tests
- [ ] API layer unit tests
- [ ] Data access layer unit tests
- [ ] Test environment and dependencies

#### Task 2.4.2: Integration tests (0.5 day)

- [ ] API integration tests
- [ ] Database integration tests
- [ ] File upload tests
- [ ] Test fixtures

#### Task 2.4.3: Performance testing and optimization (0.5 day)

- [ ] API performance tests
- [ ] Query optimization
- [ ] Caching
- [ ] File processing performance

## 📅 Phase 3: Task scheduling system (1 week)

### Work item 3.1: Celery integration (2 days)

#### Task 3.1.1: Celery configuration (0.5 day)

- [ ] Create `backend/tasks/celery_app.py`
  - [ ] Configure Celery app
  - [ ] Redis as message broker
  - [ ] Result backend
  - [ ] Task routing

#### Task 3.1.2: Processing tasks (1 day)

- [ ] Create `backend/tasks/processing_tasks.py`
  - [ ] Video processing tasks
  - [ ] 6-step pipeline tasks
  - [ ] Progress tracking
  - [ ] Status updates

#### Task 3.1.3: File processing tasks (0.5 day)

- [ ] Create `backend/tasks/file_tasks.py`
  - [ ] Upload tasks
  - [ ] File processing tasks
  - [ ] Cleanup tasks
  - [ ] Task error handling

### Work item 3.2: WebSocket implementation (2 days)

#### Task 3.2.1: WebSocket server (1 day)

- [ ] Create `backend/api/v1/websocket.py`
  - [ ] Connection management
  - [ ] Message broadcast
  - [ ] Connection authentication
  - [ ] Connection state

#### Task 3.2.2: Real-time messaging (0.5 day)

- [ ] Task progress push
- [ ] Processing status updates
- [ ] Error message push
- [ ] Message format definitions

#### Task 3.2.3: Frontend WebSocket integration (0.5 day)

- [ ] Update frontend WebSocket client
- [ ] Real-time status updates
- [ ] Reconnection logic
- [ ] Message handling

### Work item 3.3: Frontend–backend integration (2 days)

#### Task 3.3.1: API integration testing (1 day)

- [ ] Test all API endpoints
- [ ] Verify payload consistency
- [ ] Test error handling
- [ ] Verify file upload

#### Task 3.3.2: Task scheduling integration (0.5 day)

- [ ] Test task creation and start
- [ ] Verify status updates
- [ ] Test task cancellation
- [ ] Verify real-time progress

#### Task 3.3.3: End-to-end testing (0.5 day)

- [ ] Full user flow tests
- [ ] Data correctness
- [ ] Error recovery
- [ ] Performance validation

## 📊 Work item priority

### High priority (required)

1. Database model design
2. SQLAlchemy integration
3. Project API routes
4. Processing service
5. Error handling middleware

### Medium priority (important)

1. Data access layer
2. File upload API
3. Clip and collection APIs
4. Celery integration
5. WebSocket implementation

### Low priority (optional)

1. Auth middleware
2. Performance optimization
3. Advanced testing
4. Monitoring and logging

## 🛠️ Development environment

### Required tools

- [ ] Python 3.9+
- [ ] Node.js 16+
- [ ] Redis
- [ ] Git

### Development dependencies

- [ ] Poetry (Python)
- [ ] npm/yarn (Node.js)
- [ ] Docker (optional, for containers)

### Development tools

- [ ] VS Code or PyCharm
- [ ] Postman or Insomnia (API testing)
- [ ] SQLite Browser (database inspection)

## 📝 Acceptance criteria

### Phase 1

- [ ] Database models designed and tested
- [ ] SQLAlchemy integration working
- [ ] Existing data migrated successfully
- [ ] Data access layer complete

### Phase 2

- [ ] All API endpoints working
- [ ] Service layer logic correct
- [ ] Middleware functioning
- [ ] Test coverage ≥ 80%

### Phase 3

- [ ] Task scheduling working
- [ ] WebSocket real-time communication working
- [ ] Frontend–backend integration passing
- [ ] End-to-end tests passing

---

**Document version**: 1.0  
**Created**: December 2024  
**Last updated**: December 2024
