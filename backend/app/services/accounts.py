"""Local household identities with signed, HttpOnly session cookies.

This app deliberately has no provider-password flow. Provider sessions are only
created by an approved provider OAuth/device adapter, never by this service.
"""

import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database.session import get_db
from app.models.entities import AppUser, Household, PersonalLink

COOKIE_NAME = "nwf_session"
_runtime_secret = secrets.token_urlsafe(32)


def _secret():
    return settings.session_secret or _runtime_secret


def _sign(value: str):
    return hmac.new(_secret().encode(), value.encode(), hashlib.sha256).hexdigest()


def _session_value(user_id: int):
    value = str(user_id)
    return f"{value}.{_sign(value)}"


def _read_session(value: str | None):
    if not value or "." not in value:
        return None
    user_id, signature = value.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(user_id)):
        return None
    return int(user_id) if user_id.isdigit() else None


def _set_session(response: Response, user: AppUser):
    response.set_cookie(
        COOKIE_NAME,
        _session_value(user.id),
        httponly=True,
        secure=settings.session_secure_cookie,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
    )


def current_user(request: Request, response: Response, db: Session = Depends(get_db)):
    user_id = _read_session(request.cookies.get(COOKIE_NAME))
    user = db.get(AppUser, user_id) if user_id else None
    if user:
        return user
    household = Household(name="My Household")
    db.add(household)
    db.flush()
    user = AppUser(
        display_name="Owner",
        role="OWNER",
        household_id=household.id,
        csrf_token=secrets.token_urlsafe(32),
    )
    db.add(user)
    db.flush()
    # The first local owner adopts links created before household accounts existed.
    for link in db.query(PersonalLink).where(PersonalLink.owner_id.is_(None)):
        link.owner_id = user.id
    db.commit()
    db.refresh(user)
    _set_session(response, user)
    return user


def require_csrf(request: Request, user: AppUser = Depends(current_user)):
    token = request.headers.get("X-CSRF-Token", "")
    if not token or not hmac.compare_digest(token, user.csrf_token):
        raise HTTPException(403, "A valid CSRF token is required")
    return user


def session_payload(user: AppUser, db: Session):
    household = db.get(Household, user.household_id) if user.household_id else None
    return {
        "id": user.id,
        "display_name": user.display_name,
        "role": user.role,
        "household_id": user.household_id,
        "household_name": household.name if household else None,
        "csrf_token": user.csrf_token,
    }
