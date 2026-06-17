"""FastAPI application factory with exception handlers and router registration."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.routers import auth, health, movies

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application instance."""
    application = FastAPI(
        title="Movie Scraper API",
        description="Mini Movie Scraper + REST API — FunPrime Technologies",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Register routers ──────────────────────────────────
    application.include_router(auth.router)
    application.include_router(movies.router)
    application.include_router(health.router)

    # ── Exception handlers ────────────────────────────────
    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation error",
                "errors": [
                    {k: v for k, v in err.items() if k != "ctx"} for err in exc.errors()
                ],
            },
        )

    @application.exception_handler(IntegrityError)
    async def integrity_exception_handler(request: Request, exc: IntegrityError):
        logger.warning("Integrity constraint violation: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": "Resource conflict"},
        )

    @application.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    return application


app = create_app()
