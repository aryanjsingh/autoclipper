# Upload Status Page Guide

## Overview

The upload status page is dedicated to viewing and managing Bilibili upload tasks, with full task monitoring and management capabilities.

## Access

- **URL**: `http://localhost:3000/upload-status`
- **Navigation**: Click the "Upload Status" button in the top navigation bar

## Main Features

### 1. Task List

The page displays all upload tasks in a table with:

- **Task ID**: Unique identifier
- **Title**: Title of the uploaded video
- **Upload account**: Bilibili account used (nickname and username)
- **Partition**: Upload partition
- **Status**: Current task status (Pending / Processing / Success / Failed / Cancelled)
- **Progress**: Upload progress bar (0–100%)
- **File size**: Video file size
- **Created at**: Task creation time

### 2. Statistics

Stat cards at the top of the page:

- **Total tasks**: Total number of upload tasks
- **Success**: Number of completed tasks
- **Failed**: Number of failed tasks
- **In progress**: Number of tasks processing or waiting

### 3. Task Actions

Each task supports:

#### View Details
- Click "Details" for full task information
- Includes task ID, status, account, project, progress, file info, BV/AV IDs, etc.
- Shows error message if any

#### Retry Task
- "Retry" appears only for failed tasks
- Resubmits the task to the queue
- Requires confirmation

#### Cancel Task
- "Cancel" appears only for pending or processing tasks
- Stops task execution
- Requires confirmation

### 4. Auto Refresh

- Page refreshes data every 30 seconds
- Click "Refresh" for an immediate update
- Shows task status changes in real time

## Status Reference

### Task Status

| Status | Icon | Description | Available actions |
|------|------|------|------------|
| Pending | ⏰ | Task created, waiting to run | View details, Cancel |
| Processing | ▶️ | Task is running | View details, Cancel |
| Success | ✅ | Task completed successfully | View details |
| Complete | ✅ | Same as Success | View details |
| Failed | ❌ | Task failed | View details, Retry |
| Cancelled | ⏹️ | Task was cancelled | View details |

### Progress Display

- **0%**: Task not started or just started
- **1–99%**: Task in progress, shows actual progress
- **100%**: Task complete
- **Error**: Failed state shows a red progress bar

## Technical Features

### Responsive Design
- Supports different screen sizes
- Table supports horizontal scroll
- Mobile-friendly

### Performance
- Paginated display, 20 items per page by default
- Quick jump and page size adjustment
- Auto refresh to avoid excessive requests

### User Experience
- Clear status labels and icons
- Detailed confirmation prompts for actions
- Friendly error messages
- Real-time status updates

## Use Cases

### 1. Monitor Upload Progress
- View real-time status of all upload tasks
- See execution progress
- Spot issues early

### 2. Manage Upload Tasks
- Retry failed tasks
- Cancel unwanted tasks
- View detailed execution info

### 3. Troubleshooting
- View error messages to locate issues
- Review task execution history
- Refine upload strategy

## Notes

1. **Network**: Ensure frontend and backend services are running
2. **Permissions**: Only admins can retry and cancel tasks
3. **Data refresh**: The page auto-refreshes; no need to reload the browser manually
4. **Status delay**: Status changes may lag slightly; please wait

## Troubleshooting

### Page Not Accessible
- Check that the frontend runs on port 3000
- Confirm routing is configured correctly

### No Data Shown
- Check that the backend API is healthy
- Confirm database connection
- Check browser console for errors

### Action Failed
- Check network connection
- Confirm backend service status
- Read the error message shown

## Changelog

- **v1.0.0** (2025-09-11): Initial release
  - Basic task list
  - Status management and actions
  - Auto refresh
  - Responsive design
