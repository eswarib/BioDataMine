from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.core.dataset_url_finder import is_kaggle_dataset_url
from app.services.ingestion.providers.base import FetchResult, IngestProvider

logger = logging.getLogger(__name__)


class KaggleDatasetProvider(IngestProvider):
    """
    Kaggle dataset provider.
    
    Handles Kaggle dataset URLs (/datasets/<owner>/<name>).
    
    Note: Kaggle notebook URLs are resolved to individual dataset URLs
    at the API layer (routes/datasets.py), so this provider only sees
    direct dataset URLs.
    """
    name = "kaggle"

    def can_handle(self, url: str) -> bool:
        """Handle Kaggle dataset URLs only."""
        try:
            p = urlparse(url)
            if p.scheme not in ("http", "https"):
                return False
            host = (p.netloc or "").lower()
            if host not in ("kaggle.com", "www.kaggle.com"):
                return False
            
            # Only handle direct dataset URLs
            # Notebook URLs are resolved at the API layer
            return is_kaggle_dataset_url(url)
        except Exception:
            return False

    async def fetch(self, url: str, out_path: Path) -> FetchResult:
        """Fetch a single Kaggle dataset."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        dataset_ref = _parse_kaggle_dataset_ref(url)
        logger.info("Downloading Kaggle dataset: %s", dataset_ref)

        tmp_dir = out_path.parent / "_kaggle_tmp"
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(parents=True, exist_ok=True)

        def _sync_download():
            try:
                from kaggle.api.kaggle_api_extended import KaggleApi
            except Exception as e:
                raise RuntimeError("Kaggle provider requires the 'kaggle' package installed") from e

            api = KaggleApi()
            api.authenticate()
            api.dataset_download_files(dataset_ref, path=str(tmp_dir), quiet=True, unzip=False)

        await asyncio.to_thread(_sync_download)

        zips = sorted(tmp_dir.glob("*.zip"), key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)
        if not zips:
            raise RuntimeError("Kaggle download finished but no .zip file was produced")

        chosen = zips[0]
        size = chosen.stat().st_size
        if size > settings.max_download_bytes:
            raise ValueError("Download too large")

        shutil.move(str(chosen), str(out_path))
        shutil.rmtree(tmp_dir, ignore_errors=True)

        return FetchResult(
            provider=self.name,
            original_url=url,
            resolved_url=url,
        )


def _parse_kaggle_dataset_ref(url: str) -> str:
    """Extract dataset reference (owner/dataset) from a Kaggle dataset URL."""
    p = urlparse(url)
    parts = [x for x in p.path.split("/") if x]
    if len(parts) < 3 or parts[0] != "datasets":
        raise ValueError("Not a Kaggle dataset URL (expected /datasets/<owner>/<dataset>)")
    owner = parts[1]
    dataset = parts[2]
    return f"{owner}/{dataset}"








