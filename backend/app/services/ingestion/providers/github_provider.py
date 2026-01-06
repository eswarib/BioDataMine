from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.core.config import settings
from app.services.ingestion.providers.base import FetchResult, IngestProvider


class GitHubRepoProvider(IngestProvider):
    name = "github"

    def can_handle(self, url: str) -> bool:
        try:
            p = urlparse(url)
            if p.scheme not in ("http", "https"):
                return False
            host = (p.netloc or "").lower()
            if host != "github.com":
                return False
            owner, repo, _ref = _parse_github_repo_url(url)
            return bool(owner and repo)
        except Exception:
            return False

    async def fetch(self, url: str, out_path: Path) -> FetchResult:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        owner, repo, ref = _parse_github_repo_url(url)

        api_url = f"https://api.github.com/repos/{owner}/{repo}/zipball"
        if ref:
            api_url = f"{api_url}/{ref}"

        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        total = 0
        async with httpx.AsyncClient(follow_redirects=True, timeout=120, headers=headers) as client:
            async with client.stream("GET", api_url) as r:
                r.raise_for_status()
                with open(out_path, "wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > settings.max_download_bytes:
                            raise ValueError("Download too large")
                        f.write(chunk)

        return FetchResult(provider=self.name, original_url=url, resolved_url=api_url)


def _parse_github_repo_url(url: str) -> tuple[str, str, str | None]:
    p = urlparse(url)
    parts = [x for x in p.path.split("/") if x]
    if len(parts) < 2:
        raise ValueError("Not a GitHub repo URL")
    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[: -len(".git")]

    ref: str | None = None
    if len(parts) >= 4 and parts[2] == "tree":
        ref = parts[3]
    return owner, repo, ref








