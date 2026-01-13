"""
URL Resolution Models

Data models for dataset URL resolution results.
"""

from dataclasses import dataclass


@dataclass
class DatasetURLResult:
    """Result of dataset URL resolution."""
    original_url: str
    resolved_urls: list[str]
    source_type: str  # "kaggle_notebook", "kaggle_dataset", "direct", etc.
    metadata: dict | None = None













