from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.db.mongo import get_db
from app.models.datasets import (
    DatasetIngestRequest,
    DatasetIngestResponse,
    DatasetListItem,
)
from app.services.ingest import ingest_dataset

router = APIRouter()


@router.post("/ingest", response_model=DatasetIngestResponse)
async def ingest(req: DatasetIngestRequest):
    # MVP: create dataset doc immediately, then process in a background task.
    db = get_db()
    now = datetime.now(timezone.utc)
    doc = {
        "name": req.name or "Untitled dataset",
        "source_url": req.url,
        "team_id": req.team_id,
        "owner_user_id": None,  # Phase 2: from auth
        "status": "processing",
        "created_at": now,
        "summary": {"total_files": 0, "modality_counts": {}, "image_2d_count": 0, "volume_3d_count": 0},
        "meta": {},
    }
    res = await db["datasets"].insert_one(doc)
    dataset_id = str(res.inserted_id)
    asyncio.create_task(ingest_dataset(dataset_id, req.url))
    return DatasetIngestResponse(dataset_id=dataset_id, status="processing")


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
                summary=d.get("summary", {"total_files": 0, "modality_counts": {}, "image_2d_count": 0, "volume_3d_count": 0}),
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


def _object_id(s: str):
    try:
        from bson import ObjectId

        return ObjectId(s)
    except Exception as e:
        raise HTTPException(status_code=400, detail="invalid dataset id") from e


