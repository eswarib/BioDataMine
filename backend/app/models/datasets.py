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
    modality_counts: dict[str, int] = Field(default_factory=dict)
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


class DatasetListItem(BaseModel):
    dataset_id: str
    name: str
    status: DatasetStatus
    created_at: datetime
    summary: DatasetSummary


