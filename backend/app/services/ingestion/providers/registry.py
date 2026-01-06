from __future__ import annotations

from app.services.ingestion.providers.github_provider import GitHubRepoProvider
from app.services.ingestion.providers.http_provider import AuthenticatedHttpProvider, HttpProvider
from app.services.ingestion.providers.kaggle_provider import KaggleDatasetProvider


def get_providers():
    # First match wins.
    return [
        KaggleDatasetProvider(),
        GitHubRepoProvider(),
        AuthenticatedHttpProvider(),
        HttpProvider(),
    ]








