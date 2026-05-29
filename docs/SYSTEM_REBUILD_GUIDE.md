# AutoClip system rebuild guide

## 🎯 Rebuild goals

After data cleanup, the system is in a clean baseline state. You can rebuild a consistent, maintainable system from scratch.

## 📋 Current status

### **✅ Completed**

- [x] Database fully cleared (all tables empty)
- [x] Filesystem cleanup complete
- [x] Temporary files and logs removed
- [x] Clean directory structure created
- [x] Database backup saved

### **🏗️ To rebuild**

- [ ] Verify database schema
- [ ] Verify system configuration
- [ ] Reset frontend state
- [ ] Test new project creation

## 🔧 Rebuild steps

### **Step 1: Verify system basics**

1. **Check database schema**
   ```bash
   sqlite3 data/autoclip.db ".schema"
   ```

2. **Check directory structure**
   ```bash
   tree data/ -L 3
   ```

3. **Verify configuration files**
   - `backend/core/config.py`
   - `backend/core/unified_paths.py`

### **Step 2: System startup test**

1. **Start backend**
   ```bash
   cd backend
   python main.py
   ```

2. **Start frontend**
   ```bash
   cd frontend
   npm run dev
   ```

3. **Check services**
   - Backend API: http://localhost:8000/health
   - Frontend: http://localhost:3000

### **Step 3: Create a test project**

1. **Upload a test video**
   - Use the UI to upload a short video
   - Verify the project creation flow

2. **Check data consistency**
   - Verify database records
   - Verify filesystem layout
   - Verify frontend display

## 📁 Directory structure

```
data/
├── autoclip.db                 # Clean database
├── autoclip_backup_*.db        # Database backups
├── projects/                   # Empty projects directory
├── output/                     # Empty output directory
│   ├── clips/                  # Clip videos
│   ├── collections/            # Collection videos
│   └── metadata/               # Metadata
├── temp/                       # Temporary files
├── cache/                      # Cache
├── uploads/                    # Uploads
└── backups/                    # Backups
```

## 🚀 Best practices

### **1. Data management**

- Sync metadata to the database as soon as a project completes
- Run data consistency checks regularly
- Clean up temporary files and cache promptly

### **2. Path management**

- Use the unified path manager
- Avoid hard-coded paths
- Validate path configuration periodically

### **3. State synchronization**

- Keep filesystem, database, and frontend state aligned
- Use WebSocket for real-time status updates
- Provide a manual sync mechanism when needed

## 🔍 Monitoring and checks

### **1. Periodic checks**

```bash
# Database status
python scripts/check_database_status.py

# Filesystem consistency
python scripts/validate_paths.py

# Frontend state
python scripts/check_frontend_state.py
```

### **2. Data sync**

```bash
# Sync metadata for all projects
python scripts/sync_complete_metadata.py

# Sync a specific project
python scripts/sync_complete_metadata.py <project_id>
```

### **3. Path validation**

```bash
# Validate all path configuration
python scripts/validate_paths.py
```

## 🚨 Notes

### **1. Development**

- Back up important data before each test run
- Use small files for functional tests
- Clean up test data promptly

### **2. Production**

- Back up the database and important files regularly
- Monitor disk usage
- Configure log rotation and cleanup

### **3. Disaster recovery**

- Keep database backups
- Record configuration changes
- Document a recovery procedure

## 📚 Related documents

- [System architecture](SYSTEM_ARCHITECTURE.md)
- [Path fix summary](PATH_FIX_SUMMARY.md)
- [Quick start guide](../QUICK_START_GUIDE.md)

## 🎉 Rebuild completion checklist

- [ ] System starts normally
- [ ] Database connection works
- [ ] Frontend renders correctly
- [ ] Project creation flow works
- [ ] Data consistency checks pass
- [ ] Path configuration validates
- [ ] Documentation updated

---

**After rebuild, the system should provide:**

- Clear data storage architecture
- Consistent data synchronization
- Reliable path management
- Monitoring and validation tooling
- Up-to-date documentation
