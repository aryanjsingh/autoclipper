# Storage Optimization Work Breakdown

## Overall Goal
Optimize the current dual storage architecture (file system + database) into a separated storage architecture (database stores metadata + file system stores actual files) to avoid data redundancy and improve system performance.

## Work Breakdown

### Phase 1: Database Model Optimization (2-3 days)

#### 1.1 Optimize Clip Model (0.5 days)
**Current Issues:**
- The `processing_result` field stores the complete processing result data
- The `clip_metadata` field may contain redundant information

**Required Changes:**
```python
# backend/models/clip.py
class Clip(BaseModel):
    # Remove redundant fields
    # processing_result = Column(JSON, nullable=True, comment="Processing result data")  # Delete
    
    # Optimize file path fields
    video_path = Column(String(500), nullable=True, comment="Clip video file path")
    thumbnail_path = Column(String(500), nullable=True, comment="Thumbnail file path")
    
    # Keep essential metadata
    clip_metadata = Column(JSON, nullable=True, comment="Clip metadata (simplified)")
```

**Specific Work:**
- [ ] Analyze the usage of the `processing_result` field
- [ ] Determine which data needs to be retained in the database and which should be moved to the file system
- [ ] Modify the Clip model and remove redundant fields
- [ ] Create database migration script

#### 1.2 Optimize Project Model (0.5 days)
**Current Issues:**
- The `project_metadata` field may contain large amounts of file system data

**Required Changes:**
```python
# backend/models/project.py
class Project(BaseModel):
    # Add file path reference fields
    video_path = Column(String(500), nullable=True, comment="Video file path")
    subtitle_path = Column(String(500), nullable=True, comment="Subtitle file path")
    
    # Optimize metadata field
    project_metadata = Column(JSON, nullable=True, comment="Project metadata (simplified)")
```

**Specific Work:**
- [ ] Analyze the contents of the `project_metadata` field
- [ ] Add file path reference field
- [ ] Optimize metadata storage structure
- [ ] Create database migration script

#### 1.3 Optimize Collection Model (0.5 days)
**Current Issues:**
- The `collection_metadata` field may contain redundant data

**Required Changes:**
```python
# backend/models/collection.py
class Collection(BaseModel):
    # Add file path reference fields
    export_path = Column(String(500), nullable=True, comment="Collection export file path")
    
    # Optimize metadata field
    collection_metadata = Column(JSON, nullable=True, comment="Collection metadata (simplified)")
```

**Specific Work:**
- [ ] Analyze the contents of the `collection_metadata` field
- [ ] Add file path reference field
- [ ] Optimize metadata storage structure
- [ ] Create database migration script

#### 1.4 Create Database Migration (1 day)
**Specific Work:**
- [ ] Create Alembic migration script
- [ ] Test migration script
- [ ] Back up existing data
- [ ] Execute migration
- [ ] Verify data integrity

### Phase 2: Storage Service Reconstruction (3-4 days)

#### 2.1 Improve StorageService (1 day)
**Current Status:**
- Basic StorageService has been created
- Need to improve file management functions

**Features to Improve:**
```python
# backend/services/storage_service.py
class StorageService:
    def save_processing_result(self, step: str, result: Dict[str, Any]) -> str:
        """Save processing result to the file system"""
        
    def save_clip_file(self, clip_data: Dict[str, Any], clip_id: str) -> str:
        """Save clip file and return path"""
        
    def save_collection_file(self, collection_data: Dict[str, Any], collection_id: str) -> str:
        """Save collection file and return path"""
        
    def get_file_content(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get file content"""
        
    def cleanup_old_files(self, project_id: str, keep_days: int = 30):
        """Clean up old files"""
```

**Specific Work:**
- [ ] Improve file saving function
- [ ] Add file reading function
- [ ] Add file cleaning function
- [ ] Add error handling
- [ ] Add logging

#### 2.2 Refactor PipelineAdapter (1 day)
**Current Issues:**
- The `_save_clips_to_database` method stores the complete data
- The `_save_collections_to_database` method stores the complete data

**Required Changes:**
```python
# backend/services/pipeline_adapter.py
class PipelineAdapter:
    def _save_clips_to_database(self, project_id: str, clips_file: Path):
        """Save clip data to the database (metadata only)"""
        # 1. Read clip data
        # 2. Save clip files to the file system
        # 3. Save metadata to the database (path references only)
        
    def _save_collections_to_database(self, project_id: str, collections_file: Path):
        """Save collection data to the database (metadata only)"""
        # 1. Read collection data
        # 2. Save collection files to the file system
        # 3. Save metadata to the database (path references only)
```

**Specific Work:**
- [ ] Analyze the current saving logic
- [ ] Refactor to separated storage mode
- [ ] Integrate StorageService
- [ ] Test new save logic

#### 2.3 Refactor Repository Layer (1 day)
**Repositories to Modify:**
- `ClipRepository`
- `CollectionRepository`
- `ProjectRepository`

**Specific Work:**
```python
# backend/repositories/clip_repository.py
class ClipRepository(BaseRepository[Clip]):
    def create_clip(self, clip_data: Dict[str, Any]) -> Clip:
        """Create clip record (separated storage)"""
        # 1. Save clip file to the file system
        # 2. Save metadata to the database
        
    def get_clip_file(self, clip_id: str) -> Optional[Path]:
        """Get clip file path"""
        
    def get_clip_content(self, clip_id: str) -> Optional[Dict[str, Any]]:
        """Get full clip content"""
```

**Specific Work:**
- [ ] Refactor ClipRepository
- [ ] Refactor CollectionRepository
- [ ] Refactor ProjectRepository
- [ ] Add file access methods
- [ ] Test Repository functions

#### 2.4 Optimize Service Layer (0.5 days)
**Services to Modify:**
- `ClipService`
- `CollectionService`
- `ProjectService`

**Specific Work:**
- [ ] Update the Service layer to use the new storage model
- [ ] Add file access interfaces
- [ ] Optimize data return format
- [ ] Test Service functions

### Phase 3: API Layer Optimization (2 days)

#### 3.1 Optimize File Upload API (0.5 days)
**Current Issues:**
- Redundant data may be stored after file upload

**Required Changes:**
```python
# backend/api/v1/files.py
@router.post("/upload")
async def upload_files(
    files: List[UploadFile],
    project_id: str,
    db: Session = Depends(get_db)
):
    """Upload files (optimized storage)"""
    # 1. Save files to the file system
    # 2. Update file paths in the database
    # 3. Do not store file content in the database
```

**Specific Work:**
- [ ] Analyze the current file upload logic
- [ ] Optimize to only save file paths
- [ ] Add file verification
- [ ] Test upload function

#### 3.2 Optimize Data Return API (0.5 days)
**APIs to Modify:**
- `/api/v1/clips/` - Clip data API
- `/api/v1/collections/` - Collection data API
- `/api/v1/projects/` - Project data API

**Specific Work:**
```python
# backend/api/v1/clips.py
@router.get("/")
async def get_clips(
    project_id: str = Query(None),
    db: Session = Depends(get_db)
):
    """Get clip list (optimized data return)"""
    # 1. Get metadata from the database
    # 2. Load full data from the file system when needed
    # 3. Return optimized data format
```

**Specific Work:**
- [ ] Analyze the current data return logic
- [ ] Optimize to load full data on demand
- [ ] Add data caching mechanism
- [ ] Test API functionality

#### 3.3 Add File Access API (0.5 days)
**New APIs Required:**
```python
# backend/api/v1/files.py
@router.get("/clips/{clip_id}/content")
async def get_clip_content(clip_id: str, db: Session = Depends(get_db)):
    """Get full clip content"""
    
@router.get("/collections/{collection_id}/content")
async def get_collection_content(collection_id: str, db: Session = Depends(get_db)):
    """Get full collection content"""
```

**Specific Work:**
- [ ] Create file content access API
- [ ] Add access control
- [ ] Add caching mechanism
- [ ] Test API functionality

#### 3.4 Optimize Frontend API Calls (0.5 days)
**Frontend Code to Modify:**
- `frontend/src/services/api.ts`
- Related React components

**Specific Work:**
- [ ] Analyze current frontend API calls
- [ ] Optimize to load data on demand
- [ ] Add data cache
- [ ] Test frontend functionality

### Phase 4: Data Migration (1 day)

#### 4.1 Create Data Migration Script (0.5 days)
**Specific Work:**
```python
# scripts/migrate_to_optimized_storage.py
def migrate_clips_data():
    """Migrate clip data"""
    # 1. Read full data from the database
    # 2. Save to the file system
    # 3. Update database to store path references only
    
def migrate_collections_data():
    """Migrate collection data"""
    # 1. Read full data from the database
    # 2. Save to the file system
    # 3. Update database to store path references only
```

**Specific Work:**
- [ ] Create data migration script
- [ ] Add data validation
- [ ] Add rollback mechanism
- [ ] Test migration script

#### 4.2 Perform Data Migration (0.5 days)
**Specific Work:**
- [ ] Back up existing data
- [ ] Execute migration script
- [ ] Verify data integrity
- [ ] Clean up redundant data

### Phase 5: Testing and Optimization (1-2 days)

#### 5.1 Functional Test (0.5 days)
**Test Content:**
- [ ] File upload function
- [ ] Data processing function
- [ ] Data query function
- [ ] File access function

#### 5.2 Performance Test (0.5 days)
**Test Content:**
- [ ] Storage space usage
- [ ] Data access performance
- [ ] System response time
- [ ] Concurrent processing capability

#### 5.3 Optimization and Adjustment (0.5 days)
**Optimization Content:**
- [ ] Adjust configuration based on test results
- [ ] Optimize caching strategy
- [ ] Optimize file organization
- [ ] Optimize error handling

## Time Schedule

| Stage | Work Content | Estimated Time | Owner |
|------|----------|----------|--------|
| Phase 1 | Database model optimization | 2-3 days | Backend development |
| Phase 2 | Storage service reconstruction | 3-4 days | Backend development |
| Phase 3 | API layer optimization | 2 days | Backend development |
| Phase 4 | Data migration | 1 day | Backend development |
| Phase 5 | Testing and optimization | 1-2 days | Full-stack development |

**Total: 9-12 days**

## Risk Assessment

### High-Risk Items
1. **Data Migration Risk**
   - Risk: Data loss or corruption
   - Mitigation: Adequate backup, step-by-step migration, rollback mechanism

2. **API Compatibility Risk**
   - Risk: Frontend functionality affected
   - Mitigation: Keep API interfaces compatible and migrate gradually

3. **Performance Risk**
   - Risk: Decreased file access performance
   - Mitigation: Add caching mechanism, optimize file organization

### Medium-Risk Items
1. **Increased Code Complexity**
   - Risk: Increased maintenance difficulty
   - Mitigation: Good code organization, complete documentation

2. **Insufficient Test Coverage**
   - Risk: Functional defects
   - Mitigation: Comprehensive test cases, automated testing

## Success Criteria

### Functional Standards
- [ ] All existing features work properly
- [ ] Data integrity is guaranteed
- [ ] File access function is normal
- [ ] API interface remains compatible

### Performance Standards
- [ ] Storage space usage reduced by more than 10%
- [ ] Data access performance does not decrease
- [ ] System response time remains stable
- [ ] Concurrent processing capabilities remain stable

### Quality Standards
- [ ] Code coverage is no less than 80%
- [ ] No serious bugs
- [ ] Complete documentation
- [ ] Test pass rate 100%

## Follow-Up Maintenance

### Monitoring Indicators
- Storage usage
- File access performance
- Data consistency
- Error rate

### Maintenance Tasks
- Clean temporary files regularly
- Monitor storage space usage
- Optimize file organization
- Update documentation

This work breakdown covers the complete process from database model optimization to final testing to ensure that storage optimization can be implemented smoothly.
