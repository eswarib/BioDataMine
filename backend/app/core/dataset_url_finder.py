"""
Dataset URL Finder

Extracts actual dataset URLs from various source URLs.
For example, converts Kaggle notebook URLs to their input dataset URLs.
"""

import logging
import re
from urllib.parse import urlparse

from app.models.dataset_url_result import DatasetURLResult

logger = logging.getLogger(__name__)


def resolve_dataset_url(url: str) -> DatasetURLResult:
    """
    Resolve a URL to actual dataset download URLs.
    
    Handles:
    - Kaggle notebook URLs -> extracts input dataset URLs
    - Kaggle dataset URLs -> returns as-is
    - Other URLs -> returns as-is
    
    Args:
        url: The URL to resolve
        
    Returns:
        DatasetURLResult with resolved URLs
    """
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().replace("www.", "")
    
    if host == "kaggle.com":
        return _resolve_kaggle_url(url, parsed)
    
    # For other URLs, return as-is
    return DatasetURLResult(
        original_url=url,
        resolved_urls=[url],
        source_type="direct",
    )


def _resolve_kaggle_url(url: str, parsed) -> DatasetURLResult:
    """Resolve Kaggle URLs (notebooks or datasets)."""
    path_parts = [p for p in parsed.path.split("/") if p]
    
    if not path_parts:
        return DatasetURLResult(
            original_url=url,
            resolved_urls=[url],
            source_type="kaggle_unknown",
        )
    
    # Already a dataset URL
    if path_parts[0] == "datasets" and len(path_parts) >= 3:
        return DatasetURLResult(
            original_url=url,
            resolved_urls=[url],
            source_type="kaggle_dataset",
        )
    
    # Notebook/code URL - need to extract input datasets
    if path_parts[0] == "code" and len(path_parts) >= 3:
        owner = path_parts[1]
        kernel_slug = path_parts[2]
        
        dataset_urls = _get_kaggle_notebook_inputs(owner, kernel_slug)
        
        return DatasetURLResult(
            original_url=url,
            resolved_urls=dataset_urls,
            source_type="kaggle_notebook",
            metadata={
                "notebook_owner": owner,
                "notebook_slug": kernel_slug,
            },
        )
    
    # Competition URL
    if path_parts[0] == "competitions" and len(path_parts) >= 2:
        competition_slug = path_parts[1]
        return DatasetURLResult(
            original_url=url,
            resolved_urls=[url],
            source_type="kaggle_competition",
            metadata={"competition": competition_slug},
        )
    
    return DatasetURLResult(
        original_url=url,
        resolved_urls=[url],
        source_type="kaggle_unknown",
    )


def _get_kaggle_notebook_inputs(owner: str, kernel_slug: str) -> list[str]:
    """
    Get input dataset URLs for a Kaggle notebook.
    
    Uses the Kaggle API to fetch kernel metadata and extract input datasets.
    
    Args:
        owner: Notebook owner username
        kernel_slug: Notebook slug/name
        
    Returns:
        List of dataset URLs used by the notebook
    """
    dataset_urls = []
    
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        
        api = KaggleApi()
        api.authenticate()
        
        kernel_ref = f"{owner}/{kernel_slug}"
        logger.info("Fetching Kaggle notebook metadata: %s", kernel_ref)
        
        # Try to pull kernel and read metadata.json
        import tempfile
        import json
        from pathlib import Path
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            try:
                api.kernels_pull(kernel_ref, path=tmp_dir, metadata=True)
                metadata_file = Path(tmp_dir) / "kernel-metadata.json"
                
                if metadata_file.exists():
                    with open(metadata_file) as f:
                        metadata = json.load(f)
                    
                    # Extract dataset sources
                    for source in metadata.get("dataset_sources", []):
                        if "/" in source:
                            url = f"https://www.kaggle.com/datasets/{source}"
                            dataset_urls.append(url)
                            logger.info("Found dataset from metadata: %s", url)
                    
                    # Also check kernel_sources (other notebooks as input)
                    # and competition_sources
                    for source in metadata.get("competition_sources", []):
                        url = f"https://www.kaggle.com/competitions/{source}"
                        logger.info("Found competition source: %s", url)
                        
            except Exception as e:
                logger.debug("kernels_pull failed: %s", e)
        
        # If API didn't work, try scraping
        if not dataset_urls:
            dataset_urls = _scrape_notebook_inputs(owner, kernel_slug)
            
    except ImportError:
        logger.warning("Kaggle package not installed, falling back to scraping")
        dataset_urls = _scrape_notebook_inputs(owner, kernel_slug)
    except Exception as e:
        logger.warning("Kaggle API failed: %s, falling back to scraping", e)
        dataset_urls = _scrape_notebook_inputs(owner, kernel_slug)
    
    if not dataset_urls:
        logger.warning(
            "Could not find input datasets for notebook %s/%s",
            owner, kernel_slug
        )
    
    return dataset_urls


def _scrape_notebook_inputs(owner: str, kernel_slug: str) -> list[str]:
    """
    Scrape Kaggle notebook page to find input datasets.
    
    This is a fallback when the API doesn't work.
    """
    import httpx
    
    dataset_urls = []
    seen = set()
    
    # Try multiple URL patterns
    urls_to_try = [
        f"https://www.kaggle.com/code/{owner}/{kernel_slug}/input",
        f"https://www.kaggle.com/code/{owner}/{kernel_slug}",
    ]
    
    for page_url in urls_to_try:
        if dataset_urls:  # Already found some
            break
            
        try:
            logger.info("Scraping notebook inputs from: %s", page_url)
            
            with httpx.Client(follow_redirects=True, timeout=30.0) as client:
                response = client.get(page_url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                })
                
                if response.status_code != 200:
                    logger.debug("Got status %d for %s", response.status_code, page_url)
                    continue
                    
                html = response.text
                
                # Pattern 1: href="/datasets/owner/slug"
                dataset_pattern = r'href=["\']?(/datasets/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)["\']?'
                for match in re.findall(dataset_pattern, html):
                    path = match.split("?")[0].rstrip("/")
                    if path not in seen:
                        seen.add(path)
                        full_url = f"https://www.kaggle.com{path}"
                        dataset_urls.append(full_url)
                        logger.info("Found dataset: %s", full_url)
                
                # Pattern 2: "datasetRef":"owner/slug" in embedded JSON
                json_pattern = r'"datasetRef"\s*:\s*"([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"'
                for ref in re.findall(json_pattern, html):
                    if ref not in seen:
                        seen.add(ref)
                        full_url = f"https://www.kaggle.com/datasets/{ref}"
                        dataset_urls.append(full_url)
                        logger.info("Found dataset from JSON: %s", full_url)
                
                # Pattern 3: "sourceSlug":"owner/slug" patterns
                source_pattern = r'"sourceSlug"\s*:\s*"([a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+)"'
                for ref in re.findall(source_pattern, html):
                    # Check if it looks like a dataset (not a kernel)
                    if ref not in seen:
                        seen.add(ref)
                        full_url = f"https://www.kaggle.com/datasets/{ref}"
                        dataset_urls.append(full_url)
                        logger.info("Found dataset from sourceSlug: %s", full_url)
                        
        except Exception as e:
            logger.warning("Failed to scrape %s: %s", page_url, e)
    
    return dataset_urls


def is_kaggle_notebook_url(url: str) -> bool:
    """Check if a URL is a Kaggle notebook/code URL."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().replace("www.", "")
        if host != "kaggle.com":
            return False
        path_parts = [p for p in parsed.path.split("/") if p]
        return len(path_parts) >= 3 and path_parts[0] == "code"
    except Exception:
        return False


def is_kaggle_dataset_url(url: str) -> bool:
    """Check if a URL is a Kaggle dataset URL."""
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower().replace("www.", "")
        if host != "kaggle.com":
            return False
        path_parts = [p for p in parsed.path.split("/") if p]
        return len(path_parts) >= 3 and path_parts[0] == "datasets"
    except Exception:
        return False

