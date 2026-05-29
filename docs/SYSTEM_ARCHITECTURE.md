# AutoClip System Architecture

## 🏗️ Overall System Architecture

AutoClip is an automatic video clipping and collection generation system built with Python + React, using a front-end/back-end separation architecture.

### **Architecture Components**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Frontend (React)│    │ Backend (FastAPI)│   │ File System     │
│                 │    │                 │    │                 │
│ - Project mgmt  │◄──►│ - API services  │◄──►│ - Project files │
│ - Video preview │    │ - Business logic│    │ - Output files  │
│ - Status monitor│    │ - Data processing│   │ - Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │ Database (SQLite)│
                       │                 │
                       │ - Project info  │
                       │ - Clip metadata │
                       │ - Collection meta│
                       │ - Task status   │
                       └─────────────────┘
```

## 📁 Data Storage Architecture

### **1. Database Layer (SQLite)**

**Core table structure:**
- `projects`: basic project information
- `clips`: clip metadata
- `collections`: collection metadata
- `tasks`: processing task status
- `bilibili_accounts`: Bilibili account information
- `upload_records`: file upload records

**Data relationships:**
```
projects (1) ──► (N) clips
projects (1) ──► (N) collections
projects (1) ──► (N) tasks
```

### **2. File System Layer**

**Directory structure:**
```
data/
├── projects/                    # Original project files
│   └── {project_id}/           # One directory per project
│       ├── raw/                # Original video files
│       ├── step1_outline/      # Outline generation results
│       ├── step2_timeline/     # Timeline analysis
│       ├── step3_scoring/      # Content scoring
│       ├── step4_title/        # Title generation
│       ├── step5_clustering/   # Content clustering
│       └── step6_video/        # Video generation
│           ├── clips_metadata.json    # Clip metadata
│           └── collections_metadata.json # Collection metadata
├── output/                      # Final output files
│   ├── clips/                  # Clip video files
│   │   └── {project_id}/       # Organized by project
│   ├── collections/            # Collection video files
│   │   └── {project_id}/       # Organized by project
│   └── metadata/               # Global metadata
├── temp/                       # Temporary files
├── cache/                      # Cache files
├── uploads/                    # Uploaded files
└── backups/                    # Database backups
```

## 🔄 Data Flow

### **1. Project Creation Flow**

```
User uploads video → Create project record → Store original file → Start processing pipeline
     ↓
Database: new row in projects table
File system: video stored in data/projects/{project_id}/raw/
```

### **2. Video Processing Flow**

```
Original video → Subtitle extraction → Content analysis → Clip generation → Collection generation → Final output
    ↓           ↓         ↓         ↓         ↓         ↓
step1_outline → step2_timeline → step3_scoring → step4_title → step5_clustering → step6_video
```

### **3. Data Synchronization Flow**

```
File system processing complete → Metadata generated → Sync to database → Frontend display
        ↓              ↓           ↓           ↓
   clips_metadata.json → Parse metadata → Write to clips table → API response
collections_metadata.json → Parse metadata → Write to collections table → API response
```

## 🔧 Key Technical Implementation

### **1. Data Synchronization Mechanism**

- **Automatic sync**: Automatically sync metadata to the database after processing completes
- **Manual sync**: Provides sync scripts for historical data
- **Incremental sync**: Only new or modified data is synchronized

### **2. Path Management**

- **Unified path manager**: `backend/core/unified_paths.py`
- **Dynamic path detection**: Automatically detect the best output path
- **Path verification**: Periodically check path configuration consistency

### **3. Status Management**

- **Project status**: pending → processing → completed
- **Task status**: pending → running → completed/failed
- **Real-time updates**: WebSocket + polling mechanism

## 🚨 Common Issues and Solutions

### **1. Data Inconsistency**

**Symptom**: Data exists in the file system but not in the database  
**Cause**: Data sync failed or was never run  
**Solution**: Run `scripts/sync_complete_metadata.py`

### **2. Path Confusion**

**Symptom**: Files scattered across multiple directories  
**Cause**: Hardcoded paths conflict with configured paths  
**Solution**: Use the unified path manager

### **3. Abnormal Frontend Display**

**Symptom**: Backend API is normal but frontend display is wrong  
**Cause**: Frontend caching or state management issues  
**Solution**: Clear browser cache and restart the frontend service

## 📋 Maintenance and Monitoring

### **1. Regular Checks**

- **Data consistency**: Verify file system and database consistency
- **Path configuration**: Verify path configuration correctness
- **Storage space**: Monitor disk usage

### **2. Backup Strategy**

- **Database backup**: Regular SQLite database backups
- **File backup**: Backup important project files
- **Configuration backup**: Backup system configuration files

### **3. Log Monitoring**

- **Application logs**: Monitor application runtime status
- **Error logs**: Detect problems early
- **Performance logs**: Monitor system performance

## 🚀 Best Practices

### **1. Data Management**

- Run data sync scripts regularly
- Clean temporary files and cache promptly
- Keep the file system structure clear

### **2. Development Workflow**

- Clean test data before developing new features
- Use unified path configuration
- Keep documentation and comments up to date

### **3. Deployment and Operations**

- Back up production data regularly
- Monitor system resource usage
- Update dependencies and security patches promptly
