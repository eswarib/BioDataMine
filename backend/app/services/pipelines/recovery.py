from __future__ import annotations

from app.db.mongo import get_db
from app.services.pipelines.dataset_pipeline import DatasetPipeline


async def requeue_processing_datasets(pipeline: DatasetPipeline) -> int:
    """
    Best-effort recovery for the in-process queue.

    Because the DatasetPipeline queue is in-memory, a process restart can leave datasets in
    status=processing without a running job. On startup, we re-enqueue those datasets.

    This is safe for MVP because the pipeline is idempotent enough (it deletes existing file docs
    for the dataset before inserting new ones).
    """
    db = get_db()
    n = 0
    cursor = db["datasets"].find(
        {"status": "processing"},
        projection={"source_url": 1},
        sort=[("created_at", -1)],
        limit=200,
    )
    async for d in cursor:
        dataset_id = str(d["_id"])
        url = d.get("source_url")
        if not url:
            continue
        await pipeline.enqueue_dataset(dataset_id, url)
        n += 1
    return n






