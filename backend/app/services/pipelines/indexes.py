from __future__ import annotations

import logging

from app.db.mongo import get_db

logger = logging.getLogger("uvicorn.error")


async def ensure_pipeline_indexes() -> None:
    """
    Best-effort index setup for pipeline collections.

    - `datasets(dataset_id)` unique index for UUID-based dataset lookups.
    - `files(dataset_id, relpath)` speeds listing and enables idempotent upserts.
      We *try* to make it unique, but if old data contains duplicates Mongo will reject it.
    """
    db = get_db()
    
    # Datasets collection: unique index on dataset_id (UUID)
    datasets = db["datasets"]
    try:
        await datasets.create_index("dataset_id", unique=True, name="uniq_dataset_id")
    except Exception as e:
        logger.warning("Could not create unique index datasets(dataset_id): %r", e)
    
    # Files collection: composite index for dataset file lookups
    files = db["files"]
    try:
        await files.create_index([("dataset_id", 1), ("relpath", 1)], unique=True, name="uniq_dataset_relpath")
    except Exception as e:
        logger.warning("Could not create unique index files(dataset_id, relpath): %r", e)
        try:
            await files.create_index([("dataset_id", 1), ("relpath", 1)], name="idx_dataset_relpath")
        except Exception as e2:
            logger.warning("Could not create non-unique index files(dataset_id, relpath): %r", e2)







