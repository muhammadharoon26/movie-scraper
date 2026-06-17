"""Application configuration via Pydantic Settings.

All values are read from environment variables or a .env file at the project root.
No default values are provided for security-critical fields to force explicit configuration.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 720

    # ── Admin Seed ────────────────────────────────────────────
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str

    # ── TMDB ──────────────────────────────────────────────────
    TMDB_API_KEY: str

    # ── Scraper ───────────────────────────────────────────────
    SCRAPER_MAX_PAGES: int = 5
    SCRAPER_PAGE_DELAY_SECONDS: float = 0.5

    # ── Redis (Bonus) ─────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Application ───────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000


settings = Settings()
