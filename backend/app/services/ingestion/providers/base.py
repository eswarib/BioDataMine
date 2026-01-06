from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FetchResult:
    provider: str
    original_url: str
    resolved_url: str


class IngestProvider:
    name: str = "base"

    def can_handle(self, url: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    async def fetch(self, url: str, out_path: Path) -> FetchResult:  # pragma: no cover
        raise NotImplementedError








