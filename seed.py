"""Seed script — creates the initial admin user.

Usage: uv run seed.py
"""

import sys

from sqlmodel import Session

from app.config import settings
from app.database import engine
from app.services import get_user_by_username, register_user


def seed_admin() -> None:
    """Create the admin user if it does not already exist."""
    with Session(engine) as session:
        if get_user_by_username(session, settings.ADMIN_USERNAME):
            print(
                f"[seed] Admin user '{settings.ADMIN_USERNAME}' already exists. Skipping."
            )
            return
        register_user(session, settings.ADMIN_USERNAME, settings.ADMIN_PASSWORD)
        print(f"[seed] Admin user '{settings.ADMIN_USERNAME}' created successfully.")


try:
    seed_admin()
except Exception as exc:
    print(f"[seed] Failed: {exc}", file=sys.stderr)
    sys.exit(1)
