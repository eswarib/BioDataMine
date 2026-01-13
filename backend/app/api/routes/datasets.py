from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.dataset_url_finder import resolve_dataset_url
from app.db.mongo import get_db
from app.models.datasets import (
    DatasetIngestRequest,
    DatasetIngestResponse,
    DatasetListItem,
    DatasetSummaryResponse,
    FileListItem,
)
from app.services.pipelines.dataset_pipeline import get_pipeline
from app.services.pipelines.dataset_pipeline_controller import run_dataset_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_dataset_name(url: str) -> str:
    """Extract a readable name from a dataset URL."""
    from urllib.parse import urlparse
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 3 and parts[0] == "datasets":
        return parts[2].replace("-", " ").replace("_", " ").title()
    return "Untitled dataset"


@router.post("/ingest", response_model=DatasetIngestResponse)
async def ingest(req: DatasetIngestRequest):
    """
    Ingest a dataset from a URL.
    
    Supports:
    - Direct dataset URLs (Kaggle, GitHub, HTTP)
    - Kaggle notebook URLs (resolves to all input datasets, each gets unique ID)
    """
    db = get_db()
    now = datetime.now(timezone.utc)
    
    # Resolve URL to actual dataset URLs (handles notebook -> datasets conversion)
    resolved = resolve_dataset_url(req.url)
    
    logger.info(
        "URL resolution: %s -> %s (%d URLs)",
        req.url, resolved.source_type, len(resolved.resolved_urls)
    )
    
    # Create a dataset entry for each resolved URL
    dataset_ids = []
    p = get_pipeline(runner=run_dataset_pipeline)
    
    for idx, dataset_url in enumerate(resolved.resolved_urls):
        # Generate name for each dataset
        if req.name and len(resolved.resolved_urls) == 1:
            name = req.name
        elif req.name and len(resolved.resolved_urls) > 1:
            name = f"{req.name} ({idx + 1}/{len(resolved.resolved_urls)})"
        else:
            name = _extract_dataset_name(dataset_url)
        
        doc = {
            "name": name,
            "source_url": dataset_url,
            "original_request_url": req.url,  # Track the original notebook URL
            "team_id": req.team_id,
            "owner_user_id": None,  # Phase 2: from auth
            "status": "processing",
            "created_at": now,
            "summary": {
                "total_files": 0,
                "scheduled_files": 0,
                "modality_counts": {},
                "kind_counts": {},
                "ext_counts": {},
                "scheduled_ext_counts": {},
                "duplicate_basename_count": 0,
                "duplicate_basename_ext_counts": {},
                "image_2d_count": 0,
                "volume_3d_count": 0,
            },
            "meta": {
                "stage": "enqueued",
                "source_type": resolved.source_type,
                "notebook_metadata": resolved.metadata if resolved.source_type == "kaggle_notebook" else None,
            },
        }
        
        res = await db["datasets"].insert_one(doc)
        dataset_id = str(res.inserted_id)
        dataset_ids.append(dataset_id)
        
        # Enqueue the dataset URL (not the original notebook URL)
        await p.enqueue_dataset(dataset_id, dataset_url)
        
        logger.info(
            "Created dataset %s for URL %s (from %s)",
            dataset_id, dataset_url, req.url
        )
    
    # Return response with first dataset as primary, but include all IDs
    return DatasetIngestResponse(
        dataset_id=dataset_ids[0],
        status="processing",
        all_dataset_ids=dataset_ids if len(dataset_ids) > 1 else None,
        source_type=resolved.source_type,
        resolved_urls=resolved.resolved_urls if len(resolved.resolved_urls) > 1 else None,
    )


@router.get("", response_model=list[DatasetListItem])
async def list_datasets():
    db = get_db()
    cursor = db["datasets"].find({}, sort=[("created_at", -1)], limit=50)
    items: list[DatasetListItem] = []
    async for d in cursor:
        items.append(
            DatasetListItem(
                dataset_id=str(d["_id"]),
                name=d.get("name", "Untitled dataset"),
                status=d.get("status", "processing"),
                created_at=d.get("created_at", datetime.now(timezone.utc)),
                summary=d.get(
                    "summary",
                    {
                        "total_files": 0,
                        "scheduled_files": 0,
                        "modality_counts": {},
                        "kind_counts": {},
                        "ext_counts": {},
                        "scheduled_ext_counts": {},
                        "duplicate_basename_count": 0,
                        "duplicate_basename_ext_counts": {},
                        "image_2d_count": 0,
                        "volume_3d_count": 0,
                    },
                ),
            )
        )
    return items


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str):
    db = get_db()
    d = await db["datasets"].find_one({"_id": _object_id(dataset_id)})
    if not d:
        raise HTTPException(status_code=404, detail="dataset not found")
    d["_id"] = str(d["_id"])
    return d


@router.get("/{dataset_id}/summary", response_model=DatasetSummaryResponse)
async def get_dataset_summary(dataset_id: str):
    db = get_db()
    d = await db["datasets"].find_one({"_id": _object_id(dataset_id)}, projection={"summary": 1, "meta.stage": 1})
    if not d:
        raise HTTPException(status_code=404, detail="dataset not found")
    summary = d.get("summary") or {}
    stage = (d.get("meta") or {}).get("stage") or "unknown"
    modality_counts = summary.get("modality_counts") or {}
    kind_counts = summary.get("kind_counts") or {}
    ext_counts = summary.get("ext_counts") or {}
    scheduled_ext_counts = summary.get("scheduled_ext_counts") or {}
    duplicate_basename_ext_counts = summary.get("duplicate_basename_ext_counts") or {}
    total = sum(int(v) for v in modality_counts.values() if isinstance(v, (int, float)))
    modality_percentages = {}
    if total > 0:
        modality_percentages = {k: (float(v) / float(total)) * 100.0 for k, v in modality_counts.items()}
    return DatasetSummaryResponse(
        total_files=int(summary.get("total_files") or 0),
        scheduled_files=int(summary.get("scheduled_files") or 0),
        modality_counts=modality_counts,
        kind_counts=kind_counts,
        ext_counts=ext_counts,
        scheduled_ext_counts=scheduled_ext_counts,
        duplicate_basename_count=int(summary.get("duplicate_basename_count") or 0),
        duplicate_basename_ext_counts=duplicate_basename_ext_counts,
        image_2d_count=int(summary.get("image_2d_count") or 0),
        volume_3d_count=int(summary.get("volume_3d_count") or 0),
        stage=stage,
        modality_percentages=modality_percentages,
    )


@router.get("/{dataset_id}/files", response_model=list[FileListItem])
async def list_dataset_files(dataset_id: str, skip: int = 0, limit: int = 200):
    # dataset_id must exist and must be a valid ObjectId (keeps behavior consistent with GET /datasets/{dataset_id})
    _ = _object_id(dataset_id)
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip must be >= 0")
    if limit < 1 or limit > 2000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 2000")

    db = get_db()
    cursor = db["files"].find({"dataset_id": dataset_id}, sort=[("relpath", 1)], skip=skip, limit=limit)
    out: list[FileListItem] = []
    async for f in cursor:
        out.append(
            FileListItem(
                dataset_id=f.get("dataset_id", dataset_id),
                relpath=f.get("relpath", ""),
                kind=f.get("kind", "unknown"),
                modality=f.get("modality", "unknown"),
                ndim=f.get("ndim"),
                dims=f.get("dims"),
                size_bytes=int(f.get("size_bytes") or 0),
                created_at=f.get("created_at", datetime.now(timezone.utc)),
                meta=f.get("meta", {}) or {},
            )
        )
    return out


def _object_id(s: str):
    try:
        from bson import ObjectId

        return ObjectId(s)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid dataset id") from e


