from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str
    app_env: str
    openai_api_key: str
    database_url: str
    gcs_bucket_name: str
    google_application_credentials: str | None = None
    chroma_persist_directory: str
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )




@lru_cache()
def get_settings():
    return Settings()


settings=get_settings()