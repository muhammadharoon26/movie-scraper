# Movie Scraper + FastAPI Backend

A production-grade mini movie scraper and REST API that fetches trending movies and TV shows from TMDB, stores them in PostgreSQL, and exposes a JWT-protected CRUD API. We are leveraing the API request being used by https://myflixerfree.org/home

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.12+ |
| Framework | FastAPI |
| ORM | SQLModel (SQLAlchemy) |
| Database | PostgreSQL 16+ |
| Migrations | Alembic |
| Authentication | JWT (python-jose) + bcrypt |
| HTTP Client | httpx + tenacity (retry) |
| Task Queue | Celery + Redis (Bonus) |
| Package Manager | uv |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Prerequisites

- **Python 3.12+** — [python.org](https://www.python.org/downloads/)
- **uv** — Install via: `pip install uv` or `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **PostgreSQL 16+** — Installed and running locally. [postgresql.org](https://www.postgresql.org/download/)
- **Redis**
---

## Quick Start (Local)

```bash
# 1. Clone the repository
git clone https://github.com/muhammadharoon26/movie-scraper
cd movie-scraper

# 2. Copy and configure environment variables
cp .env.example .env
# Edit .env with your actual values:
#   - DATABASE_URL (your local PostgreSQL connection string)
#   - TMDB_API_KEY (your TMDB API key)
#   - JWT_SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(32))")
#   - ADMIN_USERNAME / ADMIN_PASSWORD

# 3. Create the PostgreSQL database
createdb movie_scraper

# 4. Install dependencies
uv sync

# 5. Run database migrations
uv run alembic upgrade head

# 6. Seed the admin user
uv run seed.py

# 7. Run the scraper to populate movies
uv run scrape.py

# 8. Start the API server
uv run uvicorn app.main:app --reload

# 9. Open API docs in your browser
#    http://localhost:8000/docs
```

---

## Quick Start (Docker)

```bash
# 1. Copy the example environment variables
cp .env.example .env

# 2. Boot everything with one command
docker compose up --build

# The app will automatically:
#   - Start PostgreSQL and Redis
#   - Run Alembic migrations to set up the database tables
#   - Create a default admin user
#   - Start the FastAPI server on http://localhost:8000
#   - Start the background Celery worker

# 3. Populate the Database (Run this in a NEW terminal window!)
docker compose exec app python scrape.py
# This will fetch 100 trending movies from TMDB and insert them into your database.
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/login` | No | Authenticate and get a JWT token |
| `POST` | `/auth/register` | Yes | Register a new user (admin only) |
| `GET` | `/movies` | Yes | List all movies (paginated) |
| `GET` | `/movies/{id}` | Yes | Get a single movie by UUID |
| `PATCH` | `/movies/{id}` | Yes | Update movie title or genres |
| `DELETE` | `/movies/{id}` | Yes | Soft-delete a movie |
| `GET` | `/health` | No | Health check + last scrape status |

### Authentication

1. Login to get a token:
```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your-password"}'
```

2. Use the token on protected endpoints:
```bash
curl "http://localhost:8000/movies" \
  -H "Authorization: Bearer <your-access-token>"
```

### Pagination

```bash
curl "http://localhost:8000/movies?page=1&limit=20" \
  -H "Authorization: Bearer <your-access-token>"
```

Response includes pagination metadata:
```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 87,
    "total_pages": 5
  }
}
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string |
| `JWT_SECRET_KEY` | Yes | — | Secret key for signing JWT tokens |
| `JWT_ALGORITHM` | No | `HS256` | JWT signing algorithm |
| `JWT_EXPIRE_MINUTES` | No | `720` | Token expiry in minutes |
| `ADMIN_USERNAME` | No | `admin` | Initial admin username |
| `ADMIN_PASSWORD` | Yes | — | Initial admin password |
| `TMDB_API_KEY` | Yes | — | TMDB API key for the scraper |
| `SCRAPER_MAX_PAGES` | No | `5` | Number of TMDB pages to fetch |
| `SCRAPER_PAGE_DELAY_SECONDS` | No | `0.5` | Delay between page requests |
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis URL for Celery |
| `APP_HOST` | No | `0.0.0.0` | Server bind host |
| `APP_PORT` | No | `8000` | Server bind port |

---

## Running the Scraper

```bash
# Fetch trending movies/TV from TMDB and store in the database
uv run scrape.py
```

- Fetches `SCRAPER_MAX_PAGES` pages (20 items/page) from TMDB trending endpoint.
- Uses `ON CONFLICT DO NOTHING` to skip duplicates on subsequent runs.
- Records scrape metadata in the `scrape_logs` table.

---

## Running Tests

```bash
# Requires a PostgreSQL test database
createdb movie_scraper_test

# Set the test database URL
export TEST_DATABASE_URL=postgresql://user:password@localhost:5432/movie_scraper_test

# Run all tests with coverage
uv run pytest -v --cov=app --cov-report=term-missing

# Run scraper-only tests (no database required)
uv run pytest tests/test_scraper.py -v
```

---

## Project Structure

```
movie-scraper/
├── app/
│   ├── config.py              # Pydantic Settings (reads .env)
│   ├── database.py            # SQLModel engine + session factory
│   ├── deps.py                # FastAPI dependency injection
│   ├── main.py                # App factory + exception handlers
│   ├── models.py              # SQLModel table definitions
│   ├── schemas.py             # Pydantic request/response schemas
│   ├── scraper.py             # TMDB client, parser, DB ingestion
│   ├── security.py            # JWT + bcrypt utilities
│   ├── services.py            # Auth + movie CRUD business logic
│   └── routers/
│       ├── auth.py            # Login + registration endpoints
│       ├── movies.py          # Movie CRUD endpoints
│       └── health.py          # Health check endpoint
├── tests/
│   ├── conftest.py            # Fixtures + factory helpers
│   ├── test_api.py            # Auth, movies, health endpoint tests
│   └── test_scraper.py        # Scraper parser unit tests
├── alembic/                   # Database migrations
├── scrape.py                  # CLI scraper entry point
├── seed.py                    # Admin user seeder
├── celery_app.py              # Celery background tasks
├── pyproject.toml             # Dependencies (uv)
├── Dockerfile                 # Multi-stage container build
├── docker-compose.yml         # Full-stack orchestration
├── .env.example               # Environment variable template
└── .github/workflows/ci.yml   # CI pipeline
```

---

## License

MIT

