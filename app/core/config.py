from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "LMS Assistant"
    app_env: str = "production"
    openai_api_key: str = ""
    database_url: str = ""
    gcs_bucket_name: str = "ai-lms"
    google_application_credentials: str | None = None
    chroma_persist_directory: str = "/tmp/chroma_db"
    chroma_host: str | None = None
    chroma_port: int = 8000
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )




@lru_cache()
def get_settings():
    return Settings()


settings=get_settings()