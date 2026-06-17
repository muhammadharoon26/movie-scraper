"""Scraper unit tests — parser logic (no database required)."""

from app.scraper import parse_trending_item

GENRE_MAP = {28: "Action", 12: "Adventure", 878: "Sci-Fi", 35: "Comedy", 18: "Drama"}


class TestParser:
    def test_movie_item(self):
        item = {
            "id": 1,
            "media_type": "movie",
            "title": "Film",
            "poster_path": "/a.jpg",
            "genre_ids": [28, 12],
            "release_date": "2026-06-15",
        }
        r = parse_trending_item(item, GENRE_MAP)
        assert r["tmdb_id"] == 1
        assert r["title"] == "Film"
        assert r["thumbnail_url"] == "https://image.tmdb.org/t/p/w500/a.jpg"
        assert r["genres"] == ["Action", "Adventure"]
        assert r["release_year"] == 2026
        assert r["source_url"] == "https://www.themoviedb.org/movie/1"

    def test_tv_item(self):
        item = {
            "id": 2,
            "media_type": "tv",
            "name": "Show",
            "poster_path": "/b.jpg",
            "genre_ids": [18],
            "first_air_date": "2025-01-10",
        }
        r = parse_trending_item(item, GENRE_MAP)
        assert r["title"] == "Show"
        assert r["media_type"] == "tv"
        assert r["release_year"] == 2025

    def test_missing_id(self):
        assert (
            parse_trending_item({"media_type": "movie", "title": "X"}, GENRE_MAP)
            is None
        )

    def test_missing_title(self):
        assert parse_trending_item({"id": 3, "media_type": "movie"}, GENRE_MAP) is None

    def test_null_poster(self):
        item = {
            "id": 4,
            "media_type": "movie",
            "title": "NP",
            "poster_path": None,
            "genre_ids": [],
            "release_date": "2026-01-01",
        }
        assert parse_trending_item(item, GENRE_MAP)["thumbnail_url"] is None

    def test_missing_date(self):
        item = {
            "id": 5,
            "media_type": "movie",
            "title": "ND",
            "poster_path": "/c.jpg",
            "genre_ids": [],
        }
        assert parse_trending_item(item, GENRE_MAP)["release_year"] is None

    def test_unknown_genre_ids_dropped(self):
        item = {
            "id": 6,
            "media_type": "movie",
            "title": "UG",
            "poster_path": "/d.jpg",
            "genre_ids": [28, 99999],
            "release_date": "2026-01-01",
        }
        assert parse_trending_item(item, GENRE_MAP)["genres"] == ["Action"]

    def test_malformed_date(self):
        item = {
            "id": 7,
            "media_type": "movie",
            "title": "BD",
            "poster_path": "/e.jpg",
            "genre_ids": [],
            "release_date": "bad",
        }
        assert parse_trending_item(item, GENRE_MAP)["release_year"] is None
