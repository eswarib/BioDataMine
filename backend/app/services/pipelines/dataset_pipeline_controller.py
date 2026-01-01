from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from app.core.config import settings
from app.db.mongo import get_db
from app.services.detection.format.sniff import sniff_file
from app.services.detection.modality import infer_modality
from app.services.ingestion.prepare import prepare_dataset_workspace
from app.services.pipelines.jobs import DatasetPipelineJob

# Use Uvicorn's logger so INFO logs reliably show up in container stdout.
logger = logging.getLogger("uvicorn.error")


async def run_dataset_pipeline(job: DatasetPipelineJob) -> None:
    """
    Dataset-level pipeline job:
    - Stage 1: prepare workspace (download/extract via providers)
    - Stage 2: per-file analysis fanout (format sniffing) + batch-write file docs to Mongo
    - Stage 3: stage-boundary dataset summary update + finalize
    """
    db = get_db()
    ds_oid = _object_id(job.dataset_id)

    try:
        await db["datasets"].update_one(
            {"_id": ds_oid},
            {"$set": {"status": "processing", "meta.stage": "prepare"}},
        )

        prep = await prepare_dataset_workspace(dataset_id=job.dataset_id, url=job.url)
        await db["datasets"].update_one(
            {"_id": ds_oid},
            {
                "$set": {
                    "meta.ingest.provider": prep.provider,
                    "meta.resolution.original_url": prep.original_url,
                    "meta.resolution.resolved_url": prep.resolved_url,
                    "meta.stage": "analyze_files",
                }
            },
        )

        files_col = db["files"]
        await files_col.delete_many({"dataset_id": job.dataset_id})

        batch_q: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=settings.pipeline_mongo_batch_size * 4)
        writer = asyncio.create_task(
            _batch_writer(
                dataset_id=job.dataset_id,
                q=batch_q,
                batch_size=settings.pipeline_mongo_batch_size,
                flush_seconds=settings.pipeline_batch_flush_seconds,
            ),
            name=f"batch-writer:{job.dataset_id}",
        )
        writer.add_done_callback(
            lambda t: logger.exception("dataset=%s batch-writer crashed", job.dataset_id, exc_info=t.exception())
            if t.exception()
            else None
        )

        modality_counts: Counter[str] = Counter()
        kind_counts: Counter[str] = Counter()
        ext_counts: Counter[str] = Counter()
        scheduled_ext_counts: Counter[str] = Counter()
        duplicate_basename_ext_counts: Counter[str] = Counter()
        duplicate_basename_count = 0
        _seen_basenames: set[tuple[str, str]] = set()
        dicom_series_counts: Counter[str] = Counter()
        image_2d_count = 0
        volume_3d_count = 0
        total_files = 0

        sem = asyncio.Semaphore(max(1, settings.pipeline_file_concurrency))
        now = datetime.now(timezone.utc)

        async def analyze_one(fp: Path):
            async with sem:
                info = await asyncio.to_thread(sniff_file, fp)
            relpath = str(fp.relative_to(prep.scan_root))
            # --- modality detection (heuristics+model) ---
            ocr_text = ""  # [TODO: integrate OCR extraction module if available]
            # Load the image for heuristics/module if plausible
            image_arr = None
            try:
                if info.get("kind") == "image":
                    # Open and load as np.ndarray
                    from PIL import Image
                    import numpy as np
                    with Image.open(fp) as im:
                        image_arr = np.array(im)
            except Exception:
                image_arr = None
            # folder context
            foldernames = list(fp.parent.parts[-3:])
            # run hybrid modality
            modality_model = None
            if image_arr is not None:
                modality_model = infer_modality(image_arr, fp.name, foldernames, ocr_text=ocr_text)
            else:
                modality_model = {
                    "pred": info.get("modality") or "unknown",
                    "confidence": 0.0,
                    "version": "n/a",
                    "method": "fallback",
                    "probs": {},
                    "heuristic_votes": {},
                    "sources": ["sniff_file"],
                    "details": {},
                }
            doc = {
                "dataset_id": job.dataset_id,
                "relpath": relpath,
                "abspath": str(fp),
                "kind": info.get("kind", "unknown"),
                "modality": modality_model["pred"],
                "modality_model": modality_model,
                "ndim": info.get("ndim"),
                "dims": info.get("dims"),
                "size_bytes": info.get("size_bytes"),
                "created_at": now,
                "meta": info.get("meta", {}) or {},
            }
            return fp, info, doc

        tasks: set[asyncio.Task] = set()
        completed = 0

        async def schedule(fp: Path):
            t = asyncio.create_task(analyze_one(fp))
            tasks.add(t)
            t.add_done_callback(lambda _t: tasks.discard(_t))

        scheduled = 0
        for fp in _iter_files(prep.scan_root, limit=settings.max_files_per_dataset):
            await schedule(fp)
            scheduled += 1
            ext = _file_ext(fp)
            scheduled_ext_counts[ext] += 1
            # "Duplicate file" heuristic: same basename within the dataset for a given extension.
            # This catches cases where many files share the same name across folders.
            bn_key = (ext, fp.name.lower())
            if bn_key in _seen_basenames:
                duplicate_basename_count += 1
                duplicate_basename_ext_counts[ext] += 1
            else:
                _seen_basenames.add(bn_key)
            if scheduled % 5 == 0:
                logger.info(
                    "dataset=%s stage=analyze_files scheduled=%d scan_root=%s",
                    job.dataset_id,
                    scheduled,
                    str(prep.scan_root),
                )
            while len(tasks) >= settings.pipeline_file_concurrency * 2:
                done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                for d in done:
                    fp2, info2, doc2 = d.result()
                    total_files += 1
                    completed += 1
                    _accumulate_counts(doc2, fp2, modality_counts, kind_counts, ext_counts, dicom_series_counts)
                    ndim = info2.get("ndim")
                    if isinstance(ndim, int):
                        if ndim >= 3:
                            volume_3d_count += 1
                        elif ndim == 2:
                            image_2d_count += 1
                    if writer.done():
                        # Fail fast if the writer task crashed; otherwise we can deadlock on batch_q.put().
                        exc = writer.exception()
                        raise RuntimeError("batch-writer crashed") from exc
                    await batch_q.put(doc2)
                    if completed % 10 == 0:
                        logger.info(
                            "dataset=%s stage=analyze_files completed=%d scheduled=%d queued=%d",
                            job.dataset_id,
                            completed,
                            scheduled,
                            batch_q.qsize(),
                        )

        while tasks:
            done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for d in done:
                fp2, info2, doc2 = d.result()
                total_files += 1
                completed += 1
                _accumulate_counts(doc2, fp2, modality_counts, kind_counts, ext_counts, dicom_series_counts)
                ndim = info2.get("ndim")
                if isinstance(ndim, int):
                    if ndim >= 3:
                        volume_3d_count += 1
                    elif ndim == 2:
                        image_2d_count += 1
                if writer.done():
                    exc = writer.exception()
                    raise RuntimeError("batch-writer crashed") from exc
                await batch_q.put(doc2)
                if completed % 10 == 0:
                    logger.info(
                        "dataset=%s stage=analyze_files completed=%d scheduled=%d queued=%d",
                        job.dataset_id,
                        completed,
                        scheduled,
                        batch_q.qsize(),
                    )

        await batch_q.put(None)
        await writer

        dicom_volume_count = sum(1 for _, n in dicom_series_counts.items() if n >= 2)
        volume_3d_count += dicom_volume_count

        await db["datasets"].update_one(
            {"_id": ds_oid},
            {
                "$set": {
                    "meta.stage": "finalize",
                    "summary": {
                        "total_files": total_files,
                        "scheduled_files": scheduled,
                        "modality_counts": dict(modality_counts),
                        "modalities": _build_modalities_profile(modality_counts, total_files),
                        "mixed_modality": _is_mixed_modality(modality_counts),
                        "outliers": 0,  # placeholder until OOD scoring is wired
                        "kind_counts": dict(kind_counts),
                        "ext_counts": dict(ext_counts),
                        "scheduled_ext_counts": dict(scheduled_ext_counts),
                        "duplicate_basename_count": int(duplicate_basename_count),
                        "duplicate_basename_ext_counts": dict(duplicate_basename_ext_counts),
                        "image_2d_count": image_2d_count,
                        "volume_3d_count": volume_3d_count,
                    },
                    "status": "ready",
                }
            },
        )
    except Exception as e:
        await db["datasets"].update_one(
            {"_id": ds_oid},
            {"$set": {"status": "failed", "meta.stage": "failed", "meta.last_error": repr(e)}},
        )


async def _batch_writer(dataset_id: str, q: asyncio.Queue[dict | None], batch_size: int, flush_seconds: float) -> None:
    db = get_db()
    col = db["files"]

    batch: list[dict] = []

    async def flush():
        nonlocal batch
        if not batch:
            return
        # Idempotent upserts keyed by (dataset_id, relpath).
        # This prevents duplicates and makes retries safe.
        ops = []
        for d in batch:
            relpath = d.get("relpath")
            if not relpath:
                continue
            c = dict(d)
            c.pop("_id", None)
            ops.append(
                UpdateOne(
                    {"dataset_id": dataset_id, "relpath": relpath},
                    {"$set": c},
                    upsert=True,
                )
            )

        if not ops:
            batch = []
            return

        try:
            await col.bulk_write(ops, ordered=False)
        except BulkWriteError as e:
            # With upserts, BulkWriteError usually indicates invalid docs or transient issues.
            # Log and continue so the pipeline can finish.
            details = e.details or {}
            write_errors = details.get("writeErrors") or []
            codes = sorted({int(we.get("code") or 0) for we in write_errors})
            first_msg = write_errors[0].get("errmsg") if write_errors else "unknown"
            logger.warning(
                "dataset=%s bulk upsert partial failure: ops=%d codes=%s first=%s (continuing)",
                dataset_id,
                len(ops),
                codes,
                first_msg,
            )
        except Exception:
            logger.exception("dataset=%s bulk upsert failed (ops=%d) (continuing)", dataset_id, len(ops))
        batch = []

    while True:
        try:
            item = await asyncio.wait_for(q.get(), timeout=flush_seconds)
        except asyncio.TimeoutError:
            await flush()
            continue

        if item is None:
            await flush()
            return

        batch.append(item)
        if len(batch) >= batch_size:
            await flush()


def _iter_files(root: Path, limit: int):
    n = 0
    for dirpath, _dirnames, filenames in __import__("os").walk(root):
        for fn in filenames:
            yield Path(dirpath) / fn
            n += 1
            if n >= limit:
                return


def _accumulate_counts(
    doc: dict,  # expects 'modality', 'kind', etc already set
    fp: Path,
    modality_counts: Counter[str],
    kind_counts: Counter[str],
    ext_counts: Counter[str],
    dicom_series_counts: Counter[str],
) -> None:
    modality = doc.get("modality") or "unknown"
    modality_counts[modality] += 1

    kind = doc.get("kind") or "unknown"
    kind_counts[str(kind)] += 1

    ext_counts[_file_ext(fp)] += 1

    if kind == "dicom":
        series_uid = (doc.get("meta") or {}).get("SeriesInstanceUID")
        if series_uid:
            dicom_series_counts[str(series_uid)] += 1


def _build_modalities_profile(modality_counts: Counter[str], total_files: int) -> dict:
    """
    Build profile structure:
    {
      "Ultrasound": {"percent": 63, "confidence": 0.91},
      "X-ray": {"percent": 22, "confidence": 0.95},
      "Unknown": {"percent": 15}
    }
    Confidence is a placeholder (None) until we wire model-level confidences.
    """
    res: dict[str, dict] = {}
    denom = total_files or 1
    for modality, count in modality_counts.items():
        pct = (count / denom) * 100.0
        entry = {"percent": pct}
        # placeholder: confidence unknown for now; remove if not needed
        entry["confidence"] = None
        res[str(modality)] = entry
    return res


def _is_mixed_modality(modality_counts: Counter[str]) -> bool:
    """
    Returns True if more than one non-zero modality (excluding 'unknown').
    """
    non_zero = [m for m, c in modality_counts.items() if c > 0 and m != "unknown"]
    return len(non_zero) > 1


def _file_ext(path: Path) -> str:
    sfx = [s.lower() for s in path.suffixes]
    if not sfx:
        return "none"
    if len(sfx) >= 2 and sfx[-2:] == [".nii", ".gz"]:
        return ".nii.gz"
    return sfx[-1]


def _object_id(s: str):
    from bson import ObjectId

    return ObjectId(s)


