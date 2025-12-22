from __future__ import annotations

import os
import shutil
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.core.config import settings
from app.db.mongo import get_db
from app.services.sniff import sniff_file


async def ingest_dataset(dataset_id: str, url: str) -> None:
    """
    MVP ingestion pipeline:
    - download URL to a dataset workspace
    - if zip, extract
    - walk files, sniff each, store metadata in Mongo
    - compute summary (modality counts, 2D/3D counts)
    """
    db = get_db()
    ds_oid = _object_id(dataset_id)
    root = Path(settings.data_root) / dataset_id
    download_path = root / "download.bin"
    extracted_root = root / "extracted"

    try:
        root.mkdir(parents=True, exist_ok=True)
        extracted_root.mkdir(parents=True, exist_ok=True)

        await _download(url, download_path)
        is_zip = _looks_like_zip(download_path) or url.lower().endswith(".zip")

        if is_zip:
            _safe_extract_zip(download_path, extracted_root, max_bytes=settings.max_extracted_bytes)
            scan_root = extracted_root
        else:
            # Single file ingestion
            scan_root = extracted_root
            shutil.copy2(download_path, extracted_root / _safe_name_from_url(url))

        files_col = db["files"]
        await files_col.delete_many({"dataset_id": dataset_id})

        modality_counts: Counter[str] = Counter()
        dicom_series_counts: Counter[str] = Counter()
        image_2d_count = 0
        volume_3d_count = 0  # nifti volumes + dicom series volumes (computed later)
        total_files = 0

        now = datetime.now(timezone.utc)

        for fp in _iter_files(scan_root):
            total_files += 1
            info = sniff_file(fp)

            modality = info.get("modality") or "unknown"
            modality_counts[modality] += 1

            ndim = info.get("ndim")
            if isinstance(ndim, int):
                if ndim >= 3:
                    volume_3d_count += 1
                elif ndim == 2:
                    image_2d_count += 1

            if info.get("kind") == "dicom":
                series_uid = (info.get("meta") or {}).get("SeriesInstanceUID")
                if series_uid:
                    dicom_series_counts[str(series_uid)] += 1

            await files_col.insert_one(
                {
                    "dataset_id": dataset_id,
                    "relpath": str(fp.relative_to(scan_root)),
                    "abspath": str(fp),
                    "kind": info.get("kind", "unknown"),
                    "modality": modality,
                    "ndim": ndim,
                    "dims": info.get("dims"),
                    "size_bytes": info.get("size_bytes"),
                    "created_at": now,
                    "meta": info.get("meta", {}),
                }
            )

            if total_files >= settings.max_files_per_dataset:
                break

        # Series-level volume estimation for DICOM: treat any series with >=2 instances as a 3D volume.
        dicom_volume_count = sum(1 for _, n in dicom_series_counts.items() if n >= 2)
        volume_3d_count += dicom_volume_count

        await db["datasets"].update_one(
            {"_id": ds_oid},
            {
                "$set": {
                    "status": "ready",
                    "summary": {
                        "total_files": total_files,
                        "modality_counts": dict(modality_counts),
                        "image_2d_count": image_2d_count,
                        "volume_3d_count": volume_3d_count,
                    },
                }
            },
        )
    except Exception as e:
        await db["datasets"].update_one(
            {"_id": ds_oid},
            {"$set": {"status": "failed", "meta.last_error": repr(e)}},
        )


async def _download(url: str, out_path: Path) -> None:
    if not url.startswith(("http://", "https://")):
        raise ValueError("Only http/https URLs are supported")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    total = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=120) as client:
        async with client.stream("GET", url) as r:
            r.raise_for_status()
            with open(out_path, "wb") as f:
                async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > settings.max_download_bytes:
                        raise ValueError("Download too large")
                    f.write(chunk)


def _looks_like_zip(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            sig = f.read(4)
        return sig.startswith(b"PK\x03\x04")
    except Exception:
        return False


def _safe_extract_zip(zip_path: Path, dest: Path, max_bytes: int) -> None:
    extracted = 0
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            # prevent zip slip
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                continue
            extracted += member.file_size
            if extracted > max_bytes:
                raise ValueError("Extracted data too large")
            zf.extract(member, dest)


def _iter_files(root: Path):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            yield Path(dirpath) / fn


def _safe_name_from_url(url: str) -> str:
    name = url.rsplit("/", 1)[-1] or "download.bin"
    name = name.split("?", 1)[0].split("#", 1)[0]
    name = "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", "+"))
    return name or "download.bin"


def _object_id(s: str):
    from bson import ObjectId

    return ObjectId(s)


