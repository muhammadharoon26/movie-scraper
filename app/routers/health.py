"""Health check endpoint (Bonus)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, col, select

from app.database import get_session
from app.models import ScrapeLog
from app.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check with last scrape status",
)
def health_check(session: Session = Depends(get_session)):
    """Return application status and the most recent completed scrape info."""
    last_log = session.exec(
        select(ScrapeLog)
        .where(ScrapeLog.status != "running")
        .order_by(col(ScrapeLog.started_at).desc())
        .limit(1)
    ).first()

    return HealthResponse(
        status="healthy",
        last_scrape_at=last_log.started_at if last_log else None,
        last_scrape_status=last_log.status if last_log else None,
    )
