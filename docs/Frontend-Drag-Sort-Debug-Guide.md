# Front-end Drag-and-Drop Sorting Debugging Guide

## Problem Confirmation

Through backend diagnostics, we confirmed the following:

- ✅ Backend API is fully working
- ✅ All API endpoints respond correctly
- ✅ Database data is correct
- ❌ The front end did not issue an API request (no record in the backend log)

## Problem Location

**The problem occurs on the front end!** The front-end drag-and-drop sorting function does not trigger API calls correctly.

## Front-end Debugging Steps

### 1. Open Browser Developer Tools

1. Open the project details page in your browser
2. Press `F12` or right-click → "Inspect" to open developer tools
3. Switch to the **Network** tab
4. Make sure network recording is active (the record button should be on)

### 2. Check Whether the Drag Function Is Triggered

1. Try dragging a clip within a collection
2. Watch the **Network** tab for new API requests
3. If there is no API request, the drag event is not handled correctly

### 3. Check for JavaScript Errors

1. Switch to the **Console** tab
2. Try drag-and-drop sorting
3. Check for red error messages
4. Log error information for further diagnosis

### 4. Check Whether the Component Renders Correctly

1. Inspect the collection component in the **Elements** tab
2. Confirm drag-related event handlers are bound correctly
3. Check whether component props and state are correct

## Possible Causes

### 1. Drag-and-Drop Library Problem

**Symptoms**: Drag has no effect and no visual feedback

**Check**:
- Confirm whether a drag-and-drop library is used (e.g. react-dnd, @dnd-kit)
- Check library version compatibility
- Check whether the library is configured correctly

### 2. Event Handler Not Bound

**Symptoms**: Can drag but no callback is triggered

**Check**:
- Check whether callbacks such as `onReorderClips` are passed correctly
- Confirm the component receives props correctly

### 3. State Management Issues

**Symptoms**: State is not updated after dragging

**Check**:
- Check whether the `reorderCollectionClips` method in the store is called
- Add `console.log` at the start of the method to confirm execution

### 4. API Call Intercepted

**Symptoms**: Front-end code runs but no API request is sent

**Check**:
- Check axios configuration
- Check request interceptors
- Confirm network connection is normal

## Specific Debugging Code

### Add Debug Logs in CollectionPreviewModal.tsx

```typescript
const handleReorderClips = async (newClipIds: string[]) => {
  console.log('🔄 handleReorderClips called with:', newClipIds)

  try {
    console.log('📤 Calling onReorderClips...')
    await onReorderClips?.(collection.id, newClipIds)
    console.log('✅ onReorderClips completed successfully')

    message.success('Collection order updated')
  } catch (error) {
    console.error('❌ onReorderClips failed:', error)
    message.error('Failed to update collection order')
  }
}
```

### Add Debug Logs in useProjectStore.ts

```typescript
reorderCollectionClips: async (projectId: string, collectionId: string, newClipIds: string[]) => {
  console.log('🎯 reorderCollectionClips called:', { projectId, collectionId, newClipIds })

  // ... existing code ...

  try {
    console.log('📤 Calling projectApi.reorderCollectionClips...')
    await projectApi.reorderCollectionClips(projectId, collectionId, newClipIds)
    console.log('✅ API call successful')
  } catch (error) {
    console.error('❌ API call failed:', error)
    // ... error handling ...
  }
}
```

### Add Debug Logs in api.ts

```typescript
reorderCollectionClips: (projectId: string, collectionId: string, clipIds: string[]): Promise<Collection> => {
  console.log('🌐 API call: reorderCollectionClips', { projectId, collectionId, clipIds })

  const url = `/projects/${projectId}/collections/${collectionId}/reorder`
  console.log('📡 Request URL:', url)
  console.log('📦 Request data:', clipIds)

  return api.patch(url, clipIds)
}
```

## Quick Test Method

Test the API call directly in the browser console:

```javascript
// 1. Test store method
window.useProjectStore.getState().reorderCollectionClips(
  '86f9aa12-2f35-4618-b265-74b3d9a4cf2d',
  '5e5dafc8-f29a-4705-8e87-b2bb06f2a5de',
  ['3d0bb0b6-dd8d-4105-9219-b1bce74c7b4a', '678a8c4b-16ac-4893-a8d9-1b28c3bb4c81']
)

// 2. Test API call directly
fetch('http://localhost:8000/api/v1/projects/86f9aa12-2f35-4618-b265-74b3d9a4cf2d/collections/5e5dafc8-f29a-4705-8e87-b2bb06f2a5de/reorder', {
  method: 'PATCH',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(['678a8c4b-16ac-4893-a8d9-1b28c3bb4c81', '3d0bb0b6-dd8d-4105-9219-b1bce74c7b4a'])
}).then(r => r.json()).then(console.log)
```

## Expected Results

If everything works:

1. **Network tab**: A PATCH request to `/projects/.../collections/.../reorder` appears
2. **Console tab**: Related debug log output
3. **Response**: `{"message": "Collection clips reordered successfully", "clip_ids": [...]}`
4. **UI update**: Clip order in the collection updates immediately

## Next Steps

1. Follow the steps above to debug
2. Record any error messages found
3. Locate specific issues based on errors
4. Fix issues in front-end code

## Contact Support

If this guide does not resolve the issue, please provide:

- Browser console error messages
- Screenshot of Network tab request records
- Detailed steps to reproduce
