from __future__ import annotations

import asyncio
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from app.core.config import settings
from app.db.mongo import get_db
from app.services.detection.format.sniff import sniff_file
from app.services.detection.modality import infer_modality
from app.services.ingestion.prepare import prepare_dataset_workspace
from app.utilities.pipeline_helper_functions import PipelineHelpers

if TYPE_CHECKING:
    from app.services.pipelines.jobs import DatasetPipelineJob

# Use Uvicorn's logger so INFO logs reliably show up in container stdout.
logger = logging.getLogger("uvicorn.error")


class DatasetPipelineController:
    """
    Orchestrates the dataset ingestion and analysis pipeline.
    
    Stages:
    1. prepare   - Download and extract dataset via providers
    2. analyze   - Per-file format sniffing and modality detection
    3. finalize  - Compute summary statistics and mark dataset ready
    """

    def __init__(self, job: DatasetPipelineJob):
        self.job = job
        self.dataset_id = job.dataset_id
        self.url = job.url
        self.db = get_db()
        # Query filter for this dataset (uses dataset_id field, not MongoDB _id)
        self.ds_filter = {"dataset_id": self.dataset_id}

        # Counters for summary
        self.modality_counts: Counter[str] = Counter()
        self.kind_counts: Counter[str] = Counter()
        self.ext_counts: Counter[str] = Counter()
        self.scheduled_ext_counts: Counter[str] = Counter()
        self.duplicate_basename_ext_counts: Counter[str] = Counter()
        self.duplicate_basename_count = 0
        self._seen_basenames: set[tuple[str, str]] = set()
        self.dicom_series_counts: Counter[str] = Counter()
        self.image_2d_count = 0
        self.volume_3d_count = 0
        self.total_files = 0
        self.scheduled = 0
        self.completed = 0

        # Will be set during run()
        self.prep = None
        self.batch_q: asyncio.Queue[dict | None] | None = None
        self.writer_task: asyncio.Task | None = None
        self.sem: asyncio.Semaphore | None = None
        self.now: datetime | None = None

    async def run(self) -> None:
        """Main entry point to execute the full pipeline."""
        try:
            await self._stage_prepare()
            await self._stage_analyze()
            await self._stage_finalize()
        except Exception as e:
            logger.exception("dataset=%s pipeline failed: %s", self.dataset_id, repr(e))
            await self.db["datasets"].update_one(
                self.ds_filter,
                {"$set": {"status": "failed", "meta.stage": "failed", "meta.last_error": repr(e)}},
            )

    async def _stage_prepare(self) -> None:
        """Stage 1: Download and extract the dataset."""
        logger.info("dataset=%s stage=prepare starting url=%s", self.dataset_id, self.url)
        await self.db["datasets"].update_one(
            self.ds_filter,
            {"$set": {"status": "processing", "meta.stage": "prepare"}},
        )

        self.prep = await prepare_dataset_workspace(dataset_id=self.dataset_id, url=self.url)
        logger.info(
            "dataset=%s stage=prepare completed provider=%s scan_root=%s",
            self.dataset_id,
            self.prep.provider,
            str(self.prep.scan_root),
        )

        await self.db["datasets"].update_one(
            self.ds_filter,
            {
                "$set": {
                    "meta.ingest.provider": self.prep.provider,
                    "meta.resolution.original_url": self.prep.original_url,
                    "meta.resolution.resolved_url": self.prep.resolved_url,
                    "meta.stage": "analyze_files",
                }
            },
        )

    async def _stage_analyze(self) -> None:
        """Stage 2: Analyze all files in the dataset."""
        logger.info("dataset=%s stage=analyze_files starting", self.dataset_id)

        # Clear any existing file records for this dataset (idempotent restart)
        files_col = self.db["files"]
        await files_col.delete_many({"dataset_id": self.dataset_id})

        # Set up batch writer
        self.batch_q = asyncio.Queue(maxsize=settings.pipeline_mongo_batch_size * 4)
        self.writer_task = asyncio.create_task(
            self._batch_writer(),
            name=f"batch-writer:{self.dataset_id}",
        )
        self.writer_task.add_done_callback(self._on_writer_done)

        # Concurrency control
        self.sem = asyncio.Semaphore(max(1, settings.pipeline_file_concurrency))
        self.now = datetime.now(timezone.utc)

        # Process files
        tasks: set[asyncio.Task] = set()

        for fp in PipelineHelpers.iter_files(self.prep.scan_root, limit=settings.max_files_per_dataset):
            t = asyncio.create_task(self._analyze_one(fp))
            tasks.add(t)
            # NOTE: Do NOT use add_done_callback to discard tasks - causes race condition
            # Tasks are removed in _process_completed_tasks after processing results

            self.scheduled += 1
            ext = PipelineHelpers.file_ext(fp)
            self.scheduled_ext_counts[ext] += 1

            # Track duplicate basenames
            bn_key = (ext, fp.name.lower())
            if bn_key in self._seen_basenames:
                self.duplicate_basename_count += 1
                self.duplicate_basename_ext_counts[ext] += 1
            else:
                self._seen_basenames.add(bn_key)

            if self.scheduled % 5 == 0:
                logger.info(
                    "dataset=%s stage=analyze_files scheduled=%d scan_root=%s",
                    self.dataset_id,
                    self.scheduled,
                    str(self.prep.scan_root),
                )

            # Backpressure: wait if too many tasks pending
            while len(tasks) >= settings.pipeline_file_concurrency * 2:
                await self._process_completed_tasks(tasks)

        # Drain remaining tasks
        while tasks:
            await self._process_completed_tasks(tasks)

        # Signal batch writer to stop and wait for it
        await self.batch_q.put(None)
        await self.writer_task

        logger.info(
            "dataset=%s stage=analyze_files completed total=%d scheduled=%d",
            self.dataset_id,
            self.total_files,
            self.scheduled,
        )

    async def _stage_finalize(self) -> None:
        """Stage 3: Compute final summary and mark dataset ready."""
        logger.info("dataset=%s stage=finalize starting", self.dataset_id)

        # Count DICOM volumes (series with multiple slices)
        dicom_volume_count = sum(1 for _, n in self.dicom_series_counts.items() if n >= 2)
        self.volume_3d_count += dicom_volume_count

        await self.db["datasets"].update_one(
            self.ds_filter,
            {
                "$set": {
                    "meta.stage": "finalize",
                    "summary": {
                        "total_files": self.total_files,
                        "modality_counts": dict(self.modality_counts),
                        "modalities": PipelineHelpers.build_modalities_profile(self.modality_counts, self.total_files),
                        "mixed_modality": PipelineHelpers.is_mixed_modality(self.modality_counts),
                        "outliers": 0,  # placeholder until OOD scoring is wired
                        "kind_counts": dict(self.kind_counts),
                        "ext_counts": dict(self.ext_counts),
                        "duplicate_basename_count": int(self.duplicate_basename_count),
                        "duplicate_basename_ext_counts": dict(self.duplicate_basename_ext_counts),
                        "image_2d_count": self.image_2d_count,
                        "volume_3d_count": self.volume_3d_count,
                    },
                    "status": "ready",
                }
            },
        )
        logger.info("dataset=%s stage=finalize completed status=ready", self.dataset_id)

    async def _analyze_one(self, fp: Path) -> tuple[Path, dict, dict]:
        """Analyze a single file: sniff format and detect modality."""
        logger.info("dataset=%s START analyzing file=%s", self.dataset_id, fp.name)
        try:
            async with self.sem:
                info = await asyncio.to_thread(sniff_file, fp)

            relpath = str(fp.relative_to(self.prep.scan_root))

            # Load image for heuristics if applicable
            image_arr = None
            try:
                if info.get("kind") == "image":
                    from PIL import Image
                    import numpy as np
                    with Image.open(fp) as im:
                        image_arr = np.array(im)
            except Exception:
                image_arr = None

            # Folder context for heuristics
            foldernames = list(fp.parent.parts[-3:])

            # Run hybrid modality detection
            if image_arr is not None:
                modality_model = infer_modality(
                    image_arr,
                    fp.name,
                    foldernames,
                    ocr_text="",
                    image_path=str(fp),
                    dataset_id=self.dataset_id,
                )
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
                "dataset_id": self.dataset_id,
                "relpath": relpath,
                "abspath": str(fp),
                "kind": info.get("kind", "unknown"),
                "modality": modality_model["pred"],
                "modality_model": modality_model,
                "ndim": info.get("ndim"),
                "dims": info.get("dims"),
                "size_bytes": info.get("size_bytes"),
                "created_at": self.now,
                "meta": info.get("meta", {}) or {},
            }

            logger.info("dataset=%s DONE analyzing file=%s kind=%s", self.dataset_id, fp.name, doc["kind"])
            return fp, info, doc

        except Exception as e:
            logger.exception("dataset=%s ERROR analyzing file=%s error=%s", self.dataset_id, fp.name, repr(e))
            # Return minimal doc so pipeline can continue
            return fp, {"kind": "error"}, {
                "dataset_id": self.dataset_id,
                "relpath": str(fp.relative_to(self.prep.scan_root)),
                "abspath": str(fp),
                "kind": "error",
                "modality": "unknown",
                "modality_model": {
                    "pred": "unknown", "confidence": 0.0, "version": "n/a",
                    "method": "error", "probs": {}, "heuristic_votes": {},
                    "sources": [], "details": {"error": repr(e)}
                },
                "ndim": None,
                "dims": None,
                "size_bytes": fp.stat().st_size if fp.exists() else 0,
                "created_at": self.now,
                "meta": {"error": repr(e)},
            }

    async def _process_completed_tasks(self, tasks: set[asyncio.Task]) -> None:
        """Process completed analysis tasks and queue results for writing."""
        done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for d in done:
            # Remove completed task from the set FIRST
            tasks.discard(d)
            
            fp, info, doc = d.result()
            self.total_files += 1
            self.completed += 1

            PipelineHelpers.accumulate_counts(
                doc, fp,
                self.modality_counts, self.kind_counts,
                self.ext_counts, self.dicom_series_counts
            )

            ndim = info.get("ndim")
            if isinstance(ndim, int):
                if ndim >= 3:
                    self.volume_3d_count += 1
                elif ndim == 2:
                    self.image_2d_count += 1

            # Check if writer crashed
            if self.writer_task.done():
                exc = self.writer_task.exception()
                raise RuntimeError("batch-writer crashed") from exc

            await self.batch_q.put(doc)

            if self.completed % 10 == 0:
                logger.info(
                    "dataset=%s stage=analyze_files completed=%d scheduled=%d queued=%d",
                    self.dataset_id,
                    self.completed,
                    self.scheduled,
                    self.batch_q.qsize(),
                )

    async def _batch_writer(self) -> None:
        """Background task that batches and writes file documents to MongoDB."""
        col = self.db["files"]
        batch: list[dict] = []

        async def flush():
            nonlocal batch
            if not batch:
                return

            ops = []
            for d in batch:
                relpath = d.get("relpath")
                if not relpath:
                    continue
                c = dict(d)
                c.pop("_id", None)
                ops.append(
                    UpdateOne(
                        {"dataset_id": self.dataset_id, "relpath": relpath},
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
                details = e.details or {}
                write_errors = details.get("writeErrors") or []
                codes = sorted({int(we.get("code") or 0) for we in write_errors})
                first_msg = write_errors[0].get("errmsg") if write_errors else "unknown"
                logger.warning(
                    "dataset=%s bulk upsert partial failure: ops=%d codes=%s first=%s (continuing)",
                    self.dataset_id,
                    len(ops),
                    codes,
                    first_msg,
                )
            except Exception:
                logger.exception("dataset=%s bulk upsert failed (ops=%d) (continuing)", self.dataset_id, len(ops))
            batch = []

        while True:
            try:
                item = await asyncio.wait_for(self.batch_q.get(), timeout=settings.pipeline_batch_flush_seconds)
            except asyncio.TimeoutError:
                await flush()
                continue

            if item is None:
                await flush()
                return

            batch.append(item)
            if len(batch) >= settings.pipeline_mongo_batch_size:
                await flush()

    def _on_writer_done(self, task: asyncio.Task) -> None:
        """Callback when batch writer task completes."""
        if task.exception():
            logger.exception(
                "dataset=%s batch-writer crashed",
                self.dataset_id,
                exc_info=task.exception()
            )


# -----------------------------------------------------------------------------
# Module-level entry point (for backward compatibility with DatasetPipeline)
# -----------------------------------------------------------------------------

async def run_dataset_pipeline(job: DatasetPipelineJob) -> None:
    """Entry point for the DatasetPipeline worker."""
    controller = DatasetPipelineController(job)
    await controller.run()

