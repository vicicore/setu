from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OneGov / SETU API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    cors_origins: list[str] = ["http://localhost:3000"]

    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""

    appwrite_endpoint: str = ""
    appwrite_project_id: str = ""
    appwrite_api_key: str = ""
    appwrite_bucket_id: str = ""
    max_upload_mb: int = 5
    allowed_upload_mime_types: list[str] = [
        "application/pdf",
        "image/jpeg",
        "image/png",
    ]

    n8n_webhook_base_url: str = ""
    n8n_webhook_secret: str = ""

    demo_mode_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
