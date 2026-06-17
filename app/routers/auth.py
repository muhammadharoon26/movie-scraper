"""Authentication routes — login and registration."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from app.database import get_session
from app.deps import get_current_user
from app.models import User
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserRead
from app.services import authenticate_user, register_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and obtain a JWT access token",
)
def login(body: LoginRequest, session: Session = Depends(get_session)):
    """Verify username/password and return a signed JWT."""
    result = authenticate_user(session, body.username, body.password)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )
    return result


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user (requires authentication)",
)
def register(
    body: RegisterRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new user account. Only authenticated users can register new users."""
    try:
        user = register_user(session, body.username, body.password)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        )
    return UserRead(
        id=str(user.id), username=user.username, created_at=user.created_at.isoformat()
    )
