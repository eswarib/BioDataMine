from __future__ import annotations

import logging

from app.db.mongo import get_db

logger = logging.getLogger("uvicorn.error")


async def ensure_pipeline_indexes() -> None:
    """
    Best-effort index setup for pipeline collections.

    - `files(dataset_id, relpath)` speeds listing and enables idempotent upserts.
      We *try* to make it unique, but if old data contains duplicates Mongo will reject it.
    """
    db = get_db()
    files = db["files"]
    try:
        await files.create_index([("dataset_id", 1), ("relpath", 1)], unique=True, name="uniq_dataset_relpath")
    except Exception as e:
        logger.warning("Could not create unique index files(dataset_id, relpath): %r", e)
        try:
            await files.create_index([("dataset_id", 1), ("relpath", 1)], name="idx_dataset_relpath")
        except Exception as e2:
            logger.warning("Could not create non-unique index files(dataset_id, relpath): %r", e2)







