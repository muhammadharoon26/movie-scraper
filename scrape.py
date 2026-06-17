"""Standalone scraper entry point.

Usage: uv run scrape.py
"""

import logging
import sys

from app.config import settings
from app.database import engine
from app.scraper import run_scrape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

result = run_scrape(
    api_key=settings.TMDB_API_KEY,
    max_pages=settings.SCRAPER_MAX_PAGES,
    page_delay=settings.SCRAPER_PAGE_DELAY_SECONDS,
    engine=engine,
)
if result["status"] == "failed":
    sys.exit(1)
