"""SQLModel table definitions — User, Movie, ScrapeLog."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func, Index, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlmodel import Column, Field, SQLModel


class User(SQLModel, table=True):
    """Authenticated user of the system."""

    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str = Field(max_length=64, unique=True, index=True, nullable=False)
    hashed_password: str = Field(max_length=128, nullable=False)
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )


class Movie(SQLModel, table=True):
    """Movie or TV show scraped from TMDB, with soft-delete support."""

    __tablename__ = "movies"
    __table_args__ = (
        Index(
            "ix_movie_tmdb_id_active",
            "tmdb_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_movie_source_url_active",
            "source_url",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_movie_title", "title"),
        Index("ix_movie_release_year", "release_year"),
        Index("ix_movie_deleted_at", "deleted_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(sa_column=Column(String(512), nullable=False))
    thumbnail_url: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
    genres: list[str] = Field(
        default=[], sa_column=Column(ARRAY(String), nullable=False, server_default="{}")
    )
    release_year: Optional[int] = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    source_url: str = Field(sa_column=Column(String(1024), nullable=False))
    tmdb_id: int = Field(sa_column=Column(Integer, nullable=False))
    media_type: str = Field(
        default="movie",
        sa_column=Column(String(16), nullable=False, server_default="movie"),
    )
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        ),
    )
    updated_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    deleted_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class ScrapeLog(SQLModel, table=True):
    """Records metadata for each scraper execution."""

    __tablename__ = "scrape_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    started_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    finished_at: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    total_fetched: int = Field(
        default=0, sa_column=Column(Integer, nullable=False, server_default="0")
    )
    new_inserted: int = Field(
        default=0, sa_column=Column(Integer, nullable=False, server_default="0")
    )
    duplicates_skipped: int = Field(
        default=0, sa_column=Column(Integer, nullable=False, server_default="0")
    )
    status: str = Field(sa_column=Column(String(16), nullable=False))
    error_message: Optional[str] = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )
