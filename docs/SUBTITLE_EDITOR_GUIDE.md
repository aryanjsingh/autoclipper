# Subtitle Editor Feature Guide

## Function Overview

The subtitle editor is a simple text-driven video editor that allows users to synchronously delete video content with corresponding timestamps by selecting and deleting subtitles, making it easy to quickly trim videos.

## Main Features

### 1. Word-Granular Subtitle Editing
- Supports multi-level subtitle data by word, sentence, and segment
- Timestamp positioning accurate to milliseconds
- Intelligent text segmentation and time allocation

### 2. Visual Editing Interface
- Video player on the left, subtitle editing area on the right
- Highlights subtitles at the current playing position in real time
- Supports mouse selection and keyboard selection of subtitle text
- Real-time preview of deletion effects

### 3. Smart Video Editing
- Video clip extraction based on precise timestamps
- Seamlessly splice videos after deleted segments
- Maintains the encoding format and quality of the original video

### 4. Edit History Management
- Supports undo/redo operations
- Edit operation history
- Recoverable editing state

## How to Use

### 1. Open Subtitle Editor
1. On the project details page, click on any video clip
2. In the clip details popup, click the "Subtitle Edit" button
3. The system will automatically load the word-granular subtitle data of the clip

### 2. Edit Subtitle Content
1. **Select subtitles**: Click any word or sentence in the subtitle list on the right
2. **Multi-select**: Hold Ctrl/Cmd and click multiple subtitles for multi-selection
3. **Delete selected**: Click the "Delete Selected" button to delete the selected subtitle segment
4. **Undo/Redo**: Use the undo/redo buttons on the toolbar

### 3. Preview and Save
1. **Real-time preview**: The video player on the left displays the current editing state
2. **Save edits**: Click the "Save Edits" button to apply changes
3. **Download result**: The edited video file can be downloaded after editing is complete

## Technical Architecture

### Frontend Components
- `SubtitleEditor.tsx` - Main editor component
- `ClipDetailModal.tsx` - Integrated editor entry
- `subtitleEditorApi.ts` - API service layer

### Backend Services
- `SubtitleProcessor` - Subtitle data processing
- `VideoEditor` - Video editing processing
- `subtitle_editor.py` - API interface layer

### Data Flow
1. **Subtitle parsing**: SRT file → word-granular data structure
2. **User edit**: Select delete → edit operation record
3. **Video processing**: Timeline generation → FFmpeg editing → result output

## API Interface

### Get Subtitle Data
```
GET /api/v1/subtitle-editor/{project_id}/clips/{clip_id}/subtitles
```

### Edit Video
```
POST /api/v1/subtitle-editor/{project_id}/clips/{clip_id}/edit
```

### Get Edited Video
```
GET /api/v1/subtitle-editor/{project_id}/clips/{clip_id}/edited-video
```

## Prerequisites

### 1. Subtitle Data Enhancement
- ✅ Word-granular timestamp parsing
- ✅ Subtitle data structure optimization
- ✅ Improved timestamp accuracy

### 2. Frontend Interface Design
- ✅ Two-column layout implementation
- ✅ Visual subtitle display
- ✅ Selection interaction features
- ✅ Real-time preview mechanism

### 3. Backend API Extension
- ✅ Subtitle data API
- ✅ Video editing API
- ✅ Edit history API

### 4. Video Processing Optimization
- ✅ Precise editing functionality
- ✅ Seamless splicing achieved
- ✅ Format preservation mechanism

## File Structure

```
frontend/src/
├── components/
│   ├── SubtitleEditor.tsx          # Main subtitle editor component
│   └── ClipDetailModal.tsx         # Integrated editor entry
├── services/
│   └── subtitleEditorApi.ts        # API service layer
└── types/
    └── subtitle.ts                 # Type definitions

backend/
├── utils/
│   ├── subtitle_processor.py       # Subtitle processor
│   └── video_editor.py             # Video editor
└── api/v1/
    └── subtitle_editor.py          # API interface
```

## Notes

### 1. Performance Considerations
- When processing large files, load subtitle data in batches
- Video editing may take a long time; asynchronous processing is recommended
- Edit history records consume memory; limit the number of history records

### 2. Compatibility
- Supports common SRT subtitle formats
- Supports MP4 video format
- Requires FFmpeg environment support

### 3. Error Handling
- Friendly reminder when subtitle file does not exist
- Error recovery when video editing fails
- Retry mechanism when network abnormality occurs

## Future Expansion

### 1. Feature Enhancement
- Support more subtitle formats (VTT, ASS, etc.)
- Add subtitle editing (modify text, adjust timing)
- Support audio waveform visualization

### 2. Performance Optimization
- Implement lazy loading of subtitle data
- Optimize video editing algorithm
- Add caching for editing operations

### 3. User Experience
- Add keyboard shortcut support
- Implement drag-and-drop selection
- Support batch operations

## Troubleshooting

### FAQ

1. **Subtitle data loading failed**
   - Check if the SRT file exists and is in the correct format
   - Confirm the project ID and clip ID are correct

2. **Video editing failed**
   - Check if FFmpeg is installed correctly
   - Verify the original video file exists and is readable
   - Check if there is enough disk space

3. **No response for editing operations**
   - Check network connection
   - Refresh the page and try again
   - View browser console error messages

### Debugging Methods

1. **Frontend debugging**
   - Open browser developer tools
   - View API requests from the Network tab
   - Check the Console tab for error messages

2. **Backend debugging**
   - View backend log files
   - Check API interface return status
   - Verify file paths and permissions

## Summary

The subtitle editor provides powerful video editing capabilities for the AutoClip project, allowing users to trim video content quickly and accurately through text-driven methods. This feature leverages existing subtitle processing infrastructure and builds a complete editing workflow on top of it.

With this feature, users can:
- Visually see the subtitle content of the video
- Select exactly what they want to delete
- Preview editing effects in real time
- Quickly generate edited video files

This greatly improves the efficiency and user experience of video editing, making AutoClip not only a video analysis tool, but also a practical video editing platform.
