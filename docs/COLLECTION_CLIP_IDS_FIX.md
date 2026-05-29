# Collection clip_ids mapping problem fix document
## Problem description
The front-end details page displays 12 slices, but the collection data is 0, and the slices included in the collection cannot be displayed correctly.
## Problem cause analysis
1. **Data Duplication**: Running the repair script multiple times resulted in duplicate slice data (12 instead of 6)2. **clip_ids mapping error**: The clip_ids in the collection are metadata_ids (such as "3", "4", "5"), not the actual slice UUIDs3. **Data format issue**: clip_ids are stored as strings in the database instead of JSON arrays
## Fix
### 1. Clean up duplicate data
**Issue**: Each metadata_id has two slices, resulting in duplicate data
**Solution**:```sql
DELETE FROM clips WHERE id IN (
    SELECT id FROM (
        SELECT id, ROW_NUMBER() OVER (
            PARTITION BY json_extract(clip_metadata, '$.id') 
            ORDER BY created_at
        ) as rn 
        FROM clips 
        WHERE project_id = '5c48803d-0aa7-48d7-a270-2b33e4954f25'
    ) WHERE rn > 1
);
```

### 2. Fix clip_ids mapping
**Issue**: The clip_ids in the collection are metadata_ids and need to be mapped to the actual slice UUID
**Solution**:- Create a mapping from metadata_id to clip_id- Update clip_ids field in collection_metadata
```python
# Create a mapping from metadata_id to clip_id
metadata_id_to_clip_mapping = {}
for clip in clips:
    metadata = clip.clip_metadata or {}
    metadata_id = metadata.get('id')
    if metadata_id:
        metadata_id_to_clip_mapping[str(metadata_id)] = clip.id

# map clip_ids
mapped_clip_ids = []
for metadata_id in original_clip_ids:
    if metadata_id in metadata_id_to_clip_mapping:
        mapped_clip_ids.append(metadata_id_to_clip_mapping[metadata_id])
```

### 3. Fix data format
**Issue**: clip_ids are stored in the database as strings instead of JSON arrays
**Solution**:```sql
UPDATE collections 
SET collection_metadata = json_set(
    collection_metadata, 
    '$.clip_ids', 
    json('["clip_id_1", "clip_id_2", "clip_id_3"]')
) 
WHERE project_id = '5c48803d-0aa7-48d7-a270-2b33e4954f25';
```

## Repair results
### ✅ Before repair- Number of slices: 12 (repeat)- Collection quantity: 1- Number of collection slices: 0 (clip_ids mapping error)
### ✅ After repair- Number of slices: 6 (correct)- Collection quantity: 1- Number of collection slices: 3 (correct)
### 📊 Data mapping results
**Original clip_ids**: `["3", "4", "5"]` (metadata_id)**After mapping clip_ids**: `["4ae8d564-234e-4a5f-86a3-840d65e59f59", "c8be1b33-679c-4ac6-9af6-2af21595e458", "0125c5ec-4ba5-41ac-b328-e1bc61ea9e69"]` (actual clip_id)
**Mapping relationship**:- metadata_id 3 → clip_id `4ae8d564-234e-4a5f-86a3-840d65e59f59` (AI entrepreneurship is entering the college age, and this generation of young people is beginning to overtake the curve)- metadata_id 4 → clip_id `c8be1b33-679c-4ac6-9af6-2af21595e458` (AI makes experience invalid, but makes this ability more important than ever)- metadata_id 5 → clip_id `0125c5ec-4ba5-41ac-b328-e1bc61ea9e69` (The real ability to resist risks in the next ten years lies not in skills, but in judgment)
## Created tool script
### `scripts/fix_collection_clip_ids.py`
- Automatically map metadata_id to clip_id- Update clip_ids in collection_metadata- Test the repair results
**How to use**:```bash
# Fix and test
python scripts/fix_collection_clip_ids.py --project-id <project ID>

# Test only
python scripts/fix_collection_clip_ids.py --project-id <project ID> --test-only
```

## Test results
### ✅ API testing```bash
# Clips API
curl "http://localhost:8000/api/v1/clips/?project_id=5c48803d-0aa7-48d7-a270-2b33e4954f25"
# Returns: 6 clips ✅

# Collections API
curl "http://localhost:8000/api/v1/collections/?project_id=5c48803d-0aa7-48d7-a270-2b33e4954f25"
# Returns: 1 collection with 3 clip_ids ✅
```

### ✅ Front-end testing```bash
python scripts/test_frontend_data.py
# Result: The front-end data reading test passed ✅
```

## Current status
### ✅ Working normally- Front-end data reading ✅- Slice API returns 6 slices ✅- Collection API returns 1 collection, containing 3 slices ✅- Data mapping is correct ✅
### ⚠️Needs further fixes- Collection video access (404 error)- Front-end video preview function
## Related documents
- `backend/models/collection.py` - collection model- `backend/services/collection_service.py` - Collection service- `backend/api/v1/collections.py` - Collections API- `frontend/src/services/api.ts` - Frontend API client- `scripts/fix_collection_clip_ids.py` - fix script
## Experience summary
1. **Data consistency**: Ensure that the mapping relationship between metadata_id and clip_id is correct2. **Data Format**: JSON fields need to be in the correct format (array not string)3. **Data Cleaning**: Clean duplicate data regularly to avoid data inconsistencies4. **Test Verification**: Test the API and front-end functions promptly after repair
## Next steps
1. **Fix collection video access**: Solve the 404 error of collection video URL2. **Optimize front-end experience**: Improve video preview and playback functions3. **Data Validation**: Add data consistency checking mechanism4. **Automated Repair**: Integrate repair logic into the data processing process
