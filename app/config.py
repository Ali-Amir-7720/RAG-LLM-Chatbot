from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fieldforce API"
    app_env: str = "development"
    database_url: str
    jwt_secret_key: str = "change_me_to_a_long_random_secret_in_production"
    jwt_access_token_ttl_seconds: int = 900
    refresh_token_ttl_days: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
