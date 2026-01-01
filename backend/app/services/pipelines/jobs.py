from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetPipelineJob:
    dataset_id: str
    url: str


