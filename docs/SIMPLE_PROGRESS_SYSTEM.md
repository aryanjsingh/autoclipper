# Simplified Progress System Implementation Guide

## Overview

This is a simplified progress synchronization system based on the concept of "do it stupidly but do it steadily." It uses fixed stages plus fixed weights to drive progress and no longer relies on complex subscription mechanisms.

## Core Features

- **Fixed stages**: 6 predefined stages, each with a fixed weight
- **Simple polling**: The frontend polls progress via HTTP API; no WebSocket required
- **Redis storage**: The backend uses Redis to store progress snapshots and supports persistence
- **Minimal events**: Send one event per stage transition, at most 6 times

## System Architecture

### Backend Components

1. **`backend/services/simple_progress.py`** — core progress service
   - Stage definition and weight calculation
   - Redis storage and event publishing
   - Progress snapshot management

2. **`backend/api/v1/simple_progress.py`** — API endpoints
   - `/api/v1/simple-progress/snapshot` — batch progress snapshots
   - `/api/v1/simple-progress/snapshot/{project_id}` — single project progress
   - `/api/v1/simple-progress/stages` — stage configuration

3. **`backend/services/simple_pipeline_adapter.py`** — pipeline adapter
   - Integrates progress reporting into the existing pipeline
   - Automatically sends stage transition events

### Frontend Components

1. **`frontend/src/stores/useSimpleProgressStore.ts`** — state management
   - Zustand state management
   - Polling control
   - Progress data cache

2. **`frontend/src/components/SimpleProgressBar.tsx`** — progress bar component
   - Single project progress display
   - Batch project progress display
   - Automatic polling integration

3. **`frontend/src/components/SimpleProjectCard.tsx`** — project card
   - Integrated progress display
   - Status management
   - Action buttons

## Stage Definition

```python
STAGES = [
    ("INGEST", 10),        # Download/ready
    ("SUBTITLE", 15),      # Subtitles/alignment
    ("ANALYZE", 20),       # Semantic analysis/outline
    ("HIGHLIGHT", 25),     # Clip localization/scoring
    ("EXPORT", 20),        # Export/packaging
    ("DONE", 10),          # Validation/archiving
]
```

## Progress Calculation

```python
def compute_percent(stage: str, subpercent: Optional[float] = None) -> int:
    # Accumulate weights of prior stages
    done = 0
    for s in ORDER:
        if s == stage:
            break
        done += WEIGHTS[s]
    
    # Current stage
    cur = WEIGHTS.get(stage, 0)
    
    if subpercent is None:
        return min(100, done + cur) if stage == "DONE" else min(99, done)
    else:
        return min(99, done + int(cur * subpercent / 100))
```

## Event Format

```json
{
  "project_id": "46ab50a6-....",
  "stage": "HIGHLIGHT",
  "percent": 70,
  "message": "Clip localization complete, 12 candidate segments",
  "ts": 1640995200
}
```

## How to Use

### Backend Integration

1. **Sending progress events in the pipeline**:

```python
from backend.services.simple_progress import emit_progress

# Stage transition
emit_progress(project_id, "ANALYZE", "Starting content analysis")

# Sub-progress
emit_progress(project_id, "ANALYZE", "Analyzing (50%)", subpercent=50)
```

2. **Using the simplified pipeline adapter**:

```python
from backend.services.simple_pipeline_adapter import create_simple_pipeline_adapter

adapter = create_simple_pipeline_adapter(project_id, task_id)
result = adapter.process_project_sync(video_path, srt_path)
```

### Frontend Integration

1. **Use progress state management**:

```typescript
import { useSimpleProgressStore } from '../stores/useSimpleProgressStore'

const { startPolling, stopPolling, getProgress } = useSimpleProgressStore()

// Start polling
startPolling(['project-1', 'project-2'], 2000)

// Get progress
const progress = getProgress('project-1')
```

2. **Use progress bar component**:

```tsx
import { SimpleProgressBar } from '../components/SimpleProgressBar'

<SimpleProgressBar
  projectId="project-1"
  autoStart={true}
  pollingInterval={2000}
  showDetails={true}
  onProgressUpdate={(progress) => console.log(progress)}
/>
```

3. **Use project card component**:

```tsx
import { SimpleProjectCard } from '../components/SimpleProjectCard'

<SimpleProjectCard
  project={project}
  onStartProcessing={handleStart}
  onViewDetails={handleView}
  onDelete={handleDelete}
  onRetry={handleRetry}
/>
```

## API Endpoints

### Get Progress Snapshot

```bash
# Batch
GET /api/v1/simple-progress/snapshot?project_ids=project-1&project_ids=project-2

# Single
GET /api/v1/simple-progress/snapshot/project-1
```

### Get Stage Configuration

```bash
GET /api/v1/simple-progress/stages
```

## Configuration Options

### Polling Interval

- Default: 2000ms (2 seconds)
- Recommended range: 1000–5000ms
- Adjust based on network conditions

### Stage Weights

- Total weight: 100
- Each stage weight can be adjusted to match actual processing time
- Weight distribution should reflect real time spent per stage

## Troubleshooting

### Redis Connection Failed

- The system logs a warning
- Progress event emission is skipped
- Frontend polling returns empty data

### Network Outage

- Frontend polling retries automatically
- Progress data is cached in local state
- Automatic sync after network recovery

### Stage Abnormality

- Supports failure status detection
- Automatically marked as failed
- Provides retry mechanism

## Performance Optimization

1. **Batch polling**: Fetch multiple project progress in one request
2. **Smart caching**: Avoid repeated requests for the same data
3. **Conditional polling**: Start polling only when needed
4. **Automatic cleanup**: Periodically clean up expired progress data

## Extensibility

1. **New stage**: Modify the STAGES configuration only
2. **Adjust weights**: Redistribute weight per stage
3. **Custom messages**: Stage-specific message formats supported
4. **Multi-environment**: Configure per environment

## Monitor and Debug

1. **Logging**: Detailed progress event logs
2. **Status check**: Real-time progress query
3. **Error trace**: Complete error message records
4. **Performance metrics**: Polling frequency and response time monitoring

## Migration Guide

Migrating from the old complex progress system to the simplified system:

1. **Backend migration**:
   - Replace progress callbacks with `emit_progress` calls
   - Use `SimplePipelineAdapter` instead of the old adapter
   - Remove complex WebSocket progress publishing

2. **Frontend migration**:
   - Replace old state management with `useSimpleProgressStore`
   - Replace old progress components with `SimpleProgressBar`
   - Configure polling instead of WebSocket subscription

3. **Data migration**:
   - Clean up old progress data
   - Initialize new Redis progress store
   - Update project status mapping

## Summary

This simplified progress system provides:

- ✅ **Reliability**: HTTP polling, no WebSocket dependency
- ✅ **Simplicity**: Fixed stages, easy to understand and maintain
- ✅ **Performance**: Minimized network requests, smart caching
- ✅ **Extensibility**: Easy to add stages and features
- ✅ **Debuggability**: Full logging and status tracking

Compared with the previous complex system, this solution is more stable, reliable, and easier to maintain and extend.
