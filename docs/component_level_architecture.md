# Component-level architecture (implementation-ready)

## Components
- **Frontend (React or Electron)**
  - Dataset ingest form (URL + name)
  - Dataset list / dataset detail page
  - Visualizations: pie chart by modality; tables for files/series
  - Sharing UI (team members + roles)
- **Backend API (FastAPI)**
  - URL ingestion (download/extract)
  - File sniffing + metadata extraction (DICOM/NIfTI/images)
  - Dataset summary generation (counts/percentages)
  - Auth + RBAC (Owner/Editor/Viewer)
  - Share endpoints (team/dataset memberships)
- **Workers (Phase 2)**
  - Heavy analysis/ML in Celery workers (Redis broker)
- **Storage**
  - MongoDB: metadata (datasets/files/users/teams/shares/jobs)
  - Object store: S3 (or MinIO for local), for raw files

## Minimal API (MVP)
### Dataset ingestion
- **POST** `/datasets/ingest`
  - Body: `{ "url": string, "name"?: string, "team_id"?: string }`
  - Returns: `{ "dataset_id": string, "status": "processing" }`
  - Notes:
    - MVP can run in-process; Phase 2 should enqueue a background job

### Dataset retrieval
- **GET** `/datasets`
  - Returns: list of datasets visible to the user
- **GET** `/datasets/{dataset_id}`
  - Returns: dataset metadata + summary + recent files (paged)
- **GET** `/datasets/{dataset_id}/summary`
  - Returns: `{ total_files, modality_counts, modality_percentages, image_2d_count, volume_3d_count }`

## Collaboration (Phase 2)
- **POST** `/datasets/{dataset_id}/share`
  - Body: `{ "user_id": string, "role": "owner"|"editor"|"viewer" }`
- **DELETE** `/datasets/{dataset_id}/share/{user_id}`
- **POST** `/teams`
- **POST** `/teams/{team_id}/members`

## MongoDB collections (suggested)
### `users`
```json
{ "_id": "u1", "email": "x@y.com", "created_at": "..." }
```

### `teams`
```json
{ "_id": "t1", "name": "Radiology", "created_at": "..." }
```

### `team_memberships`
```json
{ "_id": "m1", "team_id": "t1", "user_id": "u1", "role": "owner" }
```

### `datasets`
```json
{
  "_id": "d1",
  "name": "My dataset",
  "source_url": "https://...",
  "team_id": null,
  "owner_user_id": "u1",
  "status": "processing",
  "created_at": "...",
  "summary": {
    "total_files": 120,
    "modality_counts": { "CT": 70, "MR": 30, "unknown": 20 },
    "image_2d_count": 80,
    "volume_3d_count": 5
  }
}
```

### `files`
```json
{
  "_id": "f1",
  "dataset_id": "d1",
  "relpath": "study1/series2/0001.dcm",
  "kind": "dicom|nifti|image|unknown",
  "modality": "CT|MR|DX|US|unknown",
  "dims": [512,512],
  "ndim": 2,
  "size_bytes": 12345,
  "created_at": "..."
}
```

## 2D vs 3D heuristics (MVP)
- **DICOM**: treat as 3D candidate when multiple instances share the same `SeriesInstanceUID`
  - Phase 2: compute slice spacing, verify consistent orientation/position
- **NIfTI**: `ndim >= 3` => 3D (volumes)
- **PNG/JPG**: 2D

## Security constraints (recommended)
- Only allow `http/https`
- Enforce max download size + max extracted size
- Prevent zip-slip (path traversal) during extraction


