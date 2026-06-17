"""TMDB scraper — HTTP client, JSON parser, and database ingestion.

Fetches trending movies/TV from TMDB, maps JSON fields to Movie columns,
and performs idempotent batch upserts via ON CONFLICT DO NOTHING.
"""

import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy.dialects.postgresql import insert
from sqlmodel import Session
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.models import Movie, ScrapeLog

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

TMDB_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "origin": "https://myflixerfree.org",
    "referer": "https://myflixerfree.org/",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
}

_TIMEOUT = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)


# ── HTTP Client ───────────────────────────────────────────


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _get_json(url: str, params: dict | None = None) -> dict:
    """GET request with retry logic, returns parsed JSON."""
    with httpx.Client(timeout=_TIMEOUT, headers=TMDB_HEADERS) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


def fetch_trending_page(api_key: str, page: int) -> dict:
    """Fetch a single page of trending movies/TV from TMDB."""
    return _get_json(
        f"{TMDB_BASE_URL}/trending/all/week", params={"api_key": api_key, "page": page}
    )


def fetch_genre_map(api_key: str) -> dict[int, str]:
    """Fetch and merge genre ID-to-name mappings for movies and TV."""
    genre_map: dict[int, str] = {}
    for media_type in ("movie", "tv"):
        try:
            data = _get_json(
                f"{TMDB_BASE_URL}/genre/{media_type}/list", params={"api_key": api_key}
            )
            for genre in data.get("genres", []):
                genre_map[genre["id"]] = genre["name"]
        except (httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("Failed to fetch %s genres: %s", media_type, exc)
    return genre_map


# ── Parser ────────────────────────────────────────────────


def parse_trending_item(item: dict, genre_map: dict[int, str]) -> dict | None:
    """Parse a single TMDB trending result into a Movie-compatible dict.

    Returns None if the item is missing required fields (id, title/name).
    """
    tmdb_id = item.get("id")
    if tmdb_id is None:
        logger.warning("Skipping item with missing 'id'")
        return None

    media_type = item.get("media_type", "movie")
    title = item.get("title") if media_type == "movie" else item.get("name")
    if not title:
        logger.warning("Skipping tmdb_id=%s: missing title/name", tmdb_id)
        return None

    poster_path = item.get("poster_path")
    date_key = "release_date" if media_type == "movie" else "first_air_date"
    date_str = item.get(date_key, "")

    return {
        "tmdb_id": tmdb_id,
        "title": title,
        "thumbnail_url": f"{TMDB_IMAGE_BASE}{poster_path}" if poster_path else None,
        "genres": [
            genre_map[gid] for gid in item.get("genre_ids", []) if gid in genre_map
        ],
        "release_year": _parse_year(date_str),
        "source_url": f"https://www.themoviedb.org/{media_type}/{tmdb_id}",
        "media_type": media_type,
    }


def _parse_year(date_str: str) -> int | None:
    """Extract year from a TMDB date string (YYYY-MM-DD). Returns None if invalid."""
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except (ValueError, TypeError):
        return None


# ── Database Ingestion ────────────────────────────────────


def upsert_movies(session: Session, movies: list[dict]) -> tuple[int, int]:
    """Batch-insert movies, skipping duplicates via ON CONFLICT DO NOTHING.

    Returns (new_inserted, duplicates_skipped).
    """
    if not movies:
        return 0, 0

    stmt = (
        insert(Movie)
        .values(movies)
        .on_conflict_do_nothing(
            index_elements=["tmdb_id"],
            index_where=Movie.deleted_at.is_(None),  # type: ignore[union-attr]
        )
    )
    result = session.exec(stmt)  # type: ignore[arg-type]
    session.commit()

    new_inserted = result.rowcount  # type: ignore[union-attr]
    return new_inserted, len(movies) - new_inserted


def create_scrape_log(session: Session, **kwargs) -> ScrapeLog:
    """Create and persist a new ScrapeLog entry."""
    log = ScrapeLog(**kwargs)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


def update_scrape_log(session: Session, log: ScrapeLog, **kwargs) -> ScrapeLog:
    """Update an existing ScrapeLog with the provided fields."""
    for key, value in kwargs.items():
        setattr(log, key, value)
    session.add(log)
    session.commit()
    session.refresh(log)
    return log


# ── Full Scrape Pipeline ─────────────────────────────────


def run_scrape(api_key: str, max_pages: int, page_delay: float, engine) -> dict:
    """Execute the full scrape pipeline: fetch, parse, upsert, log.

    Returns a summary dict with counts and status.
    """
    genre_map = fetch_genre_map(api_key)
    logger.info("Loaded %d genre mappings", len(genre_map))

    with Session(engine) as session:
        log = create_scrape_log(
            session, started_at=datetime.now(timezone.utc), status="running"
        )
        total_fetched = total_new = total_dupes = 0

        try:
            for page in range(1, max_pages + 1):
                try:
                    data = fetch_trending_page(api_key, page)
                except Exception as exc:
                    logger.error("Failed to fetch page %d after retries: %s", page, exc)
                    break

                results = data.get("results", [])
                if not results:
                    break

                parsed = [
                    m
                    for item in results
                    if (m := parse_trending_item(item, genre_map)) is not None
                ]
                total_fetched += len(parsed)

                if parsed:
                    new, dupes = upsert_movies(session, parsed)
                    total_new += new
                    total_dupes += dupes
                    logger.info(
                        "Page %d: %d parsed, %d new, %d dupes",
                        page,
                        len(parsed),
                        new,
                        dupes,
                    )

                if page >= data.get("total_pages", 1):
                    break
                if page < max_pages:
                    time.sleep(page_delay)

            update_scrape_log(
                session,
                log,
                finished_at=datetime.now(timezone.utc),
                total_fetched=total_fetched,
                new_inserted=total_new,
                duplicates_skipped=total_dupes,
                status="success",
            )
            return {
                "status": "success",
                "total_fetched": total_fetched,
                "new_inserted": total_new,
                "duplicates_skipped": total_dupes,
            }

        except Exception as exc:
            logger.exception("Scrape failed: %s", exc)
            session.rollback()
            update_scrape_log(
                session,
                log,
                finished_at=datetime.now(timezone.utc),
                total_fetched=total_fetched,
                new_inserted=total_new,
                duplicates_skipped=total_dupes,
                status="failed",
                error_message=str(exc),
            )
            return {"status": "failed", "error": str(exc)}
