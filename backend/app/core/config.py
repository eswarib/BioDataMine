from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DATASCAN_", env_file=".env", extra="ignore")

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "datascan"

    # Local storage root for extracted datasets in MVP (Phase 2: object store)
    data_root: str = "/tmp/datascan"

    # Ingestion guardrails (bytes)
    max_download_bytes: int = 2_000_000_000  # 2GB
    max_extracted_bytes: int = 5_000_000_000  # 5GB
    max_files_per_dataset: int = 50_000

    # Providers
    github_token: str | None = None  # For GitHub API (private repos / higher rate limits)
    http_headers_json: str | None = None  # JSON dict of extra headers, e.g. {"Authorization":"Bearer ..."}
    http_basic_user: str | None = None
    http_basic_pass: str | None = None

    # Pipeline execution (in-process worker for MVP; Phase 2: Celery/Redis)
    pipeline_enabled: bool = True
    pipeline_file_concurrency: int = 32
    pipeline_mongo_batch_size: int = 10
    pipeline_batch_flush_seconds: float = 1.0


settings = Settings()


