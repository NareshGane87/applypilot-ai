from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    app_name: str = "ApplyPilot AI"
    app_env: str = "development"
    secret_key: str = "dev-only-change-me"
    database_url: str = "sqlite:///./applypilot.db"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    cors_origins: str = "http://localhost:3000"
    max_upload_mb: int = 8
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env.lower() == "production":
            if self.secret_key == "dev-only-change-me" or len(self.secret_key) < 32:
                raise ValueError("Production requires SECRET_KEY with at least 32 characters")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production requires a managed PostgreSQL DATABASE_URL")
            if "*" in [x.strip() for x in self.cors_origins.split(",")]:
                raise ValueError("Production CORS_ORIGINS must list explicit trusted origins")
        return self

settings = Settings()
