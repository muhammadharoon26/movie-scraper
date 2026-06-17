"""Pydantic request/response schemas for the API."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ── Auth ──────────────────────────────────────────────────


class LoginRequest(BaseModel):
    """POST /auth/login request body."""

    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    """POST /auth/register request body (protected)."""

    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    """Successful authentication response."""

    access_token: str
    token_type: str = "bearer"


class UserRead(BaseModel):
    """Public user representation (no password)."""

    model_config = {"from_attributes": True}

    id: str
    username: str
    created_at: str


# ── Movies ────────────────────────────────────────────────


class MovieUpdate(BaseModel):
    """PATCH /movies/{id} — only title and genres are updatable."""

    title: Optional[str] = Field(default=None, min_length=1, max_length=512)
    genres: Optional[list[str]] = Field(default=None)

    @model_validator(mode="after")
    def at_least_one_field(self):
        if self.title is None and self.genres is None:
            raise ValueError("At least one of 'title' or 'genres' must be provided")
        return self


class MovieRead(BaseModel):
    """Single movie response."""

    model_config = {"from_attributes": True}

    id: uuid.UUID
    title: str
    thumbnail_url: Optional[str] = None
    genres: list[str] = []
    release_year: Optional[int] = None
    source_url: str
    media_type: str
    created_at: datetime
    updated_at: Optional[datetime] = None


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    page: int
    limit: int
    total: int
    total_pages: int


class MovieListResponse(BaseModel):
    """Paginated movie list response."""

    data: list[MovieRead]
    meta: PaginationMeta


# ── Common ────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str


class HealthResponse(BaseModel):
    """GET /health response."""

    status: str
    last_scrape_at: Optional[datetime] = None
    last_scrape_status: Optional[str] = None
