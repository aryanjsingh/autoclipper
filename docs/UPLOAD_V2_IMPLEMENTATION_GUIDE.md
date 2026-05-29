# Upload Feature v2.0 Implementation Guide

## Overview

Based on the implementation approach of the [biliup-rs](https://github.com/biliup/biliup-rs) project, we rebuilt the Bilibili upload feature with support for multiple upload routes, intelligent route selection, and complete error handling.

## New Features

### 🚀 Core Features
- **Multiple upload routes**: Supports routes such as bda2, qn, alia, bldsa, tx, txa, and bda
- **Intelligent route selection**: Automatically speed-tests and selects the best upload route
- **Chunked upload**: Supports chunked upload for large files to improve stability
- **Complete error handling**: Detailed error messages and retry mechanism
- **Progress tracking**: Real-time upload progress and status updates

### 🔧 Technical Improvements
- **Based on biliup-rs**: Draws on a mature implementation
- **Async processing**: Full asynchronous upload flow
- **Cookie management**: Fixed the encryption system to support the correct key format
- **API compatibility**: Fully compatible with the existing system

## Architecture

### File Structure
```
backend/services/
├── bilibili_service.py          # Original service (updated)
├── bilibili_upload_v2.py        # New v2.0 upload implementation
└── bilibili_service_backup.py   # Backup file
```

### Core Classes
- `BilibiliUploaderV2`: Core uploader that handles upload logic
- `BilibiliUploadServiceV2`: Upload service that manages upload flow and status

## Usage Steps

### 1. Re-import Cookie

Because the encryption system has been updated, you need to re-import your Bilibili Cookie:

1. **Get Cookie**:
   - Log in to Bilibili on the web
   - Open Developer Tools (F12)
   - In the Network tab, find any request
   - Copy the Cookie value

2. **Import Cookie**:
   - Visit the upload status page: `http://localhost:3000/upload-status`
   - Click the "Upload Status" button to open Bilibili management
   - On the "Account Management" tab, click "Add Account"
   - Choose "Cookie Login"
   - Paste the full Cookie string

### 2. Test Upload

1. **Check account status**:
   - Ensure the account status shows as "Active"
   - Verify the Cookie is valid

2. **Create upload task**:
   - On the project details page, select a video clip
   - Click "Upload to Bilibili"
   - Fill in title, description, tags, etc.
   - Select upload account and partition

3. **Monitor upload progress**:
   - View task progress on the upload status page
   - Monitor upload status and error messages in real time

## Technical Details

### Upload Flow
```
1. Verify login → 2. Pre-upload to get ID → 3. Select best route
    ↓
4. Chunk upload → 5. Merge chunks → 6. Submit upload → 7. Return BV ID
```

### Upload Routes
| Route | Provider | Notes |
|------|--------|------|
| bda2 | Baidu Cloud | Default route, good stability |
| qn | Qiniu | Fast speed |
| alia | Alibaba Cloud (overseas) | Optimized for overseas access |
| bldsa | Bilibili self-hosted | Official route |
| tx | Tencent Cloud | Optimized for China |
| txa | Tencent Cloud (overseas) | Overseas optimization |
| bda | Baidu Cloud (overseas) | Overseas optimization |

### Error Handling
- **Network errors**: Auto-retry, up to 3 times
- **Authentication errors**: Prompt to log in again
- **File errors**: Check file format and size
- **API errors**: Display detailed error messages

## Configuration

### Environment Variables
```bash
# Encryption key (auto-generated)
export ENCRYPTION_KEY="BekpMhcsOolyI_n9Hz9NxzLqMgll3vfa9qJYPOxtQXM="
```

### Upload Parameters
```python
metadata = {
    'title': 'Video title',           # Max 80 characters
    'description': 'Video description',  # Max 2000 characters
    'tags': ['tag1', 'tag2'],         # Tag list
    'partition_id': 3                 # Partition ID
}
```

## Troubleshooting

### Common Issues

1. **Cookie decryption failed**
   - Cause: Old encryption key was used
   - Fix: Re-import Cookie

2. **Upload failed**
   - Cause: Network issues or API limits
   - Fix: Check network connection, try a different route

3. **File too large**
   - Cause: Exceeds Bilibili 8GB limit
   - Fix: Compress video or split file

4. **Abnormal account status**
   - Cause: Cookie expired or invalid
   - Fix: Log in again and get a new Cookie

### Debugging

1. **View logs**:
   ```bash
   tail -f logs/celery.log
   ```

2. **Check database**:
   ```sql
   SELECT * FROM bilibili_upload_records ORDER BY created_at DESC LIMIT 5;
   ```

3. **Test API**:
   ```bash
   curl -s http://localhost:8000/api/v1/upload/records | jq .
   ```

## Performance Optimization

### Upload Speed
- **Concurrent upload**: Supports concurrent upload of multiple chunks
- **Route selection**: Automatically selects the fastest route
- **Retry mechanism**: Smart retry for failed chunks

### Stability
- **Error recovery**: Automatically handles network interruptions
- **Status sync**: Real-time upload status updates
- **Data integrity**: Ensures complete file upload

## Changelog

### v2.0.0 (2025-09-11)
- ✅ Reimplemented upload based on biliup-rs
- ✅ Multiple upload routes and intelligent selection
- ✅ Fixed Cookie encryption system
- ✅ Improved error handling and retry mechanism
- ✅ Added detailed upload progress tracking

### Planned
- 🔄 Multi-part (multi-P) upload support
- 🔄 Upload queue management
- 🔄 Resume from breakpoint
- 🔄 Batch upload support

## Related Links

- [biliup-rs project](https://github.com/biliup/biliup-rs)
- [Bilibili upload API docs](https://github.com/biliup/biliup-rs)
- [Upload Status Page Guide](./UPLOAD_STATUS_PAGE_GUIDE.md)
