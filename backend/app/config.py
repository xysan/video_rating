from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str
    JWT_SECRET: str = Field(min_length=32)
    JWT_EXPIRE_MINUTES: int = Field(default=60, gt=0)
    CORS_ORIGINS: str = ""
    FEISHU_APP_ID: str = ""
    FEISHU_APP_SECRET: str = ""
    FEISHU_APP_TOKEN: str = ""
    FEISHU_TABLE_ID: str = ""
    SYNC_INTERVAL_MINUTES: int = Field(default=15, gt=0)
    BILIBILI_CACHE_ENABLED: bool = True
    FEISHU_SYNC_ENABLED: bool = False
    FEISHU_UP_NAME_FIELD: str = "up主"
    FEISHU_TITLE_FIELD: str = "标题"
    FEISHU_PUBLISH_DATE_FIELD: str = "发布时间"
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
