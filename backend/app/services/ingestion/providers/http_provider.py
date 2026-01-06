from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from app.core.config import settings
from app.services.ingestion.providers.base import FetchResult, IngestProvider


class HttpProvider(IngestProvider):
    name = "http"

    def can_handle(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    async def fetch(self, url: str, out_path: Path) -> FetchResult:
        resolved = await _resolve_dataset_url(url)
        await _download_http(resolved, out_path)
        return FetchResult(provider=self.name, original_url=url, resolved_url=resolved)


class AuthenticatedHttpProvider(IngestProvider):
    name = "auth_http"

    def can_handle(self, url: str) -> bool:
        if not url.startswith(("http://", "https://")):
            return False
        return bool(settings.http_headers_json or (settings.http_basic_user and settings.http_basic_pass))

    async def fetch(self, url: str, out_path: Path) -> FetchResult:
        resolved = await _resolve_dataset_url(url, force_auth=True)
        await _download_http(resolved, out_path, force_auth=True)
        return FetchResult(provider=self.name, original_url=url, resolved_url=resolved)


async def _download_http(url: str, out_path: Path, force_auth: bool = False) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    headers = _extra_headers() if force_auth else None
    auth = _basic_auth() if force_auth else None

    total = 0
    async with httpx.AsyncClient(follow_redirects=True, timeout=120, headers=headers, auth=auth) as client:
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


async def _resolve_dataset_url(url: str, force_auth: bool = False) -> str:
    lowered = url.lower()
    if lowered.endswith((".zip", ".nii", ".nii.gz", ".dcm", ".png", ".jpeg", ".jpg")):
        return url

    html = await _fetch_text_preview(url, max_bytes=512 * 1024, force_auth=force_auth)
    if not html:
        return url

    parser = _HrefParser()
    try:
        parser.feed(html)
    except Exception:
        return url

    base_host = urlparse(url).netloc
    candidates: list[str] = []
    for href in parser.hrefs:
        abs_url = urljoin(url, href)
        p = urlparse(abs_url)
        if p.scheme not in ("http", "https"):
            continue
        if not p.netloc:
            continue
        if p.netloc != base_host:
            continue
        candidates.append(abs_url)

    best = _pick_best_download_candidate(candidates)
    return best or url


async def _fetch_text_preview(url: str, max_bytes: int, force_auth: bool = False) -> str | None:
    try:
        headers = _extra_headers() if force_auth else None
        auth = _basic_auth() if force_auth else None
        async with httpx.AsyncClient(follow_redirects=True, timeout=30, headers=headers, auth=auth) as client:
            async with client.stream("GET", url, headers={"Accept": "text/html,application/xhtml+xml"}) as r:
                r.raise_for_status()

                total = 0
                chunks: list[bytes] = []
                async for chunk in r.aiter_bytes(chunk_size=64 * 1024):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    total += len(chunk)
                    if total >= max_bytes:
                        break
                blob = b"".join(chunks)

        head = blob.lstrip()[:200].lower()
        if b"<html" not in head and b"<!doctype html" not in head and b"<a " not in blob[:4096].lower():
            return None
        return blob.decode("utf-8", errors="ignore")
    except Exception:
        return None


class _HrefParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        for k, v in attrs:
            if k.lower() == "href" and isinstance(v, str) and v:
                self.hrefs.append(v)


def _pick_best_download_candidate(urls: list[str]) -> str | None:
    def score(u: str) -> tuple[int, int]:
        lu = u.lower()
        if lu.endswith(".zip"):
            s = 100
        elif lu.endswith(".nii.gz"):
            s = 90
        elif lu.endswith(".nii"):
            s = 85
        elif lu.endswith(".dcm"):
            s = 80
        elif lu.endswith((".png", ".jpeg", ".jpg")):
            s = 70
        else:
            s = 0
        if "download" in lu:
            s += 10
        return (s, -len(lu))

    ranked = sorted(urls, key=score, reverse=True)
    if not ranked:
        return None
    if score(ranked[0])[0] <= 0:
        return None
    return ranked[0]


def _extra_headers() -> dict[str, str] | None:
    if not settings.http_headers_json:
        return None
    try:
        raw = json.loads(settings.http_headers_json)
        if isinstance(raw, dict):
            return {str(k): str(v) for k, v in raw.items()}
    except Exception:
        return None
    return None


def _basic_auth() -> tuple[str, str] | None:
    if settings.http_basic_user and settings.http_basic_pass:
        return (settings.http_basic_user, settings.http_basic_pass)
    return None








