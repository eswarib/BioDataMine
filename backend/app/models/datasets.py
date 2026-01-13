from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DatasetStatus = Literal["processing", "ready", "failed"]
FileKind = Literal["dicom", "nifti", "image", "unknown"]


class DatasetIngestRequest(BaseModel):
    url: str
    name: str | None = None
    team_id: str | None = None


class DatasetSummary(BaseModel):
    total_files: int = 0
    scheduled_files: int = 0
    modality_counts: dict[str, int] = Field(default_factory=dict)
    modalities: dict[str, dict] = Field(default_factory=dict)
    mixed_modality: bool | None = None
    outliers: int = 0
    kind_counts: dict[str, int] = Field(default_factory=dict)
    ext_counts: dict[str, int] = Field(default_factory=dict)
    scheduled_ext_counts: dict[str, int] = Field(default_factory=dict)
    duplicate_basename_count: int = 0
    duplicate_basename_ext_counts: dict[str, int] = Field(default_factory=dict)
    image_2d_count: int = 0
    volume_3d_count: int = 0


class DatasetDoc(BaseModel):
    id: str = Field(alias="_id")
    name: str
    source_url: str
    team_id: str | None = None
    owner_user_id: str | None = None
    status: DatasetStatus
    created_at: datetime
    summary: DatasetSummary = Field(default_factory=DatasetSummary)
    meta: dict[str, Any] = Field(default_factory=dict)


class DatasetIngestResponse(BaseModel):
    dataset_id: str
    status: DatasetStatus
    # For notebook URLs that resolve to multiple datasets
    all_dataset_ids: list[str] | None = None
    source_type: str = "direct"  # "direct", "kaggle_notebook", etc.
    resolved_urls: list[str] | None = None


class DatasetListItem(BaseModel):
    dataset_id: str
    name: str
    status: DatasetStatus
    created_at: datetime
    summary: DatasetSummary


class DatasetSummaryResponse(DatasetSummary):
    stage: str = "unknown"
    modality_percentages: dict[str, float] = Field(default_factory=dict)


class FileListItem(BaseModel):
    dataset_id: str
    relpath: str
    kind: FileKind
    modality: str
    modality_model: dict = Field(default_factory=dict)
    ndim: int | None = None
    dims: list[int] | None = None
    size_bytes: int = 0
    created_at: datetime
    meta: dict[str, Any] = Field(default_factory=dict)


