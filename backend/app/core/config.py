from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "ClinicStock"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "clinicstock-insecure-dev-secret-change-in-prod-xyz987"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Database settings (environment-driven, works with local PostgreSQL & Neon)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/clinicstock"
    SYNC_DATABASE_URL: Optional[str] = None

    # Connection pooling settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_PRE_PING: bool = True

    # CORS settings (comma-separated origins)
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return ["http://localhost:5173", "http://127.0.0.1:5173"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @model_validator(mode="after")
    def assemble_db_urls(self) -> "Settings":
        # Normalize DATABASE_URL for async SQLAlchemy
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # asyncpg requires ?ssl=... instead of ?sslmode=... (Neon default parameter)
        if "sslmode=" in url and "asyncpg" in url:
            url = url.replace("sslmode=", "ssl=")
        self.DATABASE_URL = url

        # Auto-derive SYNC_DATABASE_URL if not provided (needed for Alembic with psycopg2)
        if not self.SYNC_DATABASE_URL:
            if self.DATABASE_URL.startswith("postgresql+asyncpg://"):
                sync_url = self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
                if "ssl=" in sync_url and "sslmode=" not in sync_url:
                    sync_url = sync_url.replace("ssl=", "sslmode=")
                self.SYNC_DATABASE_URL = sync_url
            elif self.DATABASE_URL.startswith("sqlite+aiosqlite://"):
                self.SYNC_DATABASE_URL = self.DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://", 1)
            else:
                self.SYNC_DATABASE_URL = self.DATABASE_URL
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
