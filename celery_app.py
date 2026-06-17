"""Celery app + background scrape task (Bonus).

Usage: uv run celery -A celery_app worker --loglevel=info
"""

from celery import Celery

from app.config import settings

celery_app = Celery("worker", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="trigger_scrape")
def trigger_scrape() -> dict:
    """Run the movie scraper as a Celery background task."""
    from app.database import engine
    from app.scraper import run_scrape

    return run_scrape(
        api_key=settings.TMDB_API_KEY,
        max_pages=settings.SCRAPER_MAX_PAGES,
        page_delay=settings.SCRAPER_PAGE_DELAY_SECONDS,
        engine=engine,
    )
