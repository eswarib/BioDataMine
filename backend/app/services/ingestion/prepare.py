from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings
from app.services.ingestion.providers.registry import get_providers


@dataclass(frozen=True)
class PrepareResult:
    provider: str
    original_url: str
    resolved_url: str
    scan_root: Path


async def prepare_dataset_workspace(dataset_id: str, url: str) -> PrepareResult:
    """
    Prepare the local workspace for a dataset:
    - download URL to /data_root/<dataset_id>/download.bin
    - if zip, extract under /data_root/<dataset_id>/extracted
    - if single file, copy into extracted/ with safe filename

    Returns the scan_root (directory to walk for files).
    """
    root = Path(settings.data_root) / dataset_id
    download_path = root / "download.bin"
    extracted_root = root / "extracted"

    root.mkdir(parents=True, exist_ok=True)
    extracted_root.mkdir(parents=True, exist_ok=True)

    fetch = await _fetch_to_path(url, download_path)

    is_zip = _looks_like_zip(download_path) or fetch.resolved_url.lower().endswith(".zip")
    if is_zip:
        _safe_extract_zip(download_path, extracted_root, max_bytes=settings.max_extracted_bytes)
        scan_root = extracted_root
    else:
        scan_root = extracted_root
        shutil.copy2(download_path, extracted_root / _safe_name_from_url(fetch.resolved_url))

    return PrepareResult(
        provider=fetch.provider,
        original_url=fetch.original_url,
        resolved_url=fetch.resolved_url,
        scan_root=scan_root,
    )


async def _fetch_to_path(url: str, out_path: Path):
    for provider in get_providers():
        if provider.can_handle(url):
            return await provider.fetch(url, out_path)
    raise ValueError("No provider found for URL")


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
            member_path = Path(member.filename)
            if member_path.is_absolute() or ".." in member_path.parts:
                continue
            extracted += member.file_size
            if extracted > max_bytes:
                raise ValueError("Extracted data too large")
            zf.extract(member, dest)


def _safe_name_from_url(url: str) -> str:
    name = url.rsplit("/", 1)[-1] or "download.bin"
    name = name.split("?", 1)[0].split("#", 1)[0]
    name = "".join(c for c in name if c.isalnum() or c in ("-", "_", ".", "+"))
    return name or "download.bin"


