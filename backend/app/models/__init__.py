from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# 所有业务表统一使用 MySQL 8 的存储引擎与字符集。
TABLE_OPTIONS = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}


class User(Base):
    __tablename__ = "users"
    __table_args__ = TABLE_OPTIONS.copy()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(191), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(Enum("admin", "member", name="user_role", create_constraint=True, validate_strings=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())


class VideoSnapshot(Base):
    __tablename__ = "video_snapshots"
    __table_args__ = TABLE_OPTIONS.copy()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    feishu_record_id: Mapped[str] = mapped_column(String(191), unique=True)
    up_name: Mapped[str] = mapped_column(String(255))
    video_title: Mapped[str] = mapped_column(Text)
    publish_date: Mapped[date] = mapped_column(Date)
    raw_payload: Mapped[dict] = mapped_column(JSON)
    last_modified_at: Mapped[datetime] = mapped_column(DateTime)
    synced_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())


class AlgorithmConfig(Base):
    __tablename__ = "algorithm_configs"
    __table_args__ = TABLE_OPTIONS.copy()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(String(191), unique=True)
    config_value: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    # 按项目约束仅存操作者 ID，不添加外键。
    updated_by: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp())


class Score(Base):
    __tablename__ = "scores"
    __table_args__ = TABLE_OPTIONS.copy()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_snapshot_id: Mapped[int] = mapped_column(ForeignKey("video_snapshots.id", name="fk_scores_video_snapshot_id"))
    score: Mapped[Decimal] = mapped_column(Numeric(18, 6))
    score_detail: Mapped[dict] = mapped_column(JSON)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    algorithm_version: Mapped[str] = mapped_column(String(191))
