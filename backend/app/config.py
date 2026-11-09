from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_SECRET: str
    JWT_EXPIRE_MINUTES: int = 60
    CORS_ORIGINS: str = ""
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_APP_TOKEN: str = ""
    FEISHU_TABLE_ID: str = ""
    SYNC_INTERVAL_MINUTES: int = 15
    FEISHU_SYNC_ENABLED: bool = False
    SEED_ADMIN_PASSWORD: str = ""

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if make_url(value).drivername not in {"mysql+pymysql", "sqlite"}:
            raise ValueError("仅支持 MySQL 或临时本地 SQLite 连接串")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
