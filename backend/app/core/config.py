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


settings = Settings()


