"""
auth.py — API key, session token, and PIN authentication
"""
import os
from datetime import datetime, timedelta

from fastapi import Header, HTTPException, Cookie
from jose import jwt, JWTError
from passlib.context import CryptContext

APPS_SCRIPT_KEY = os.getenv("APPS_SCRIPT_KEY", "")
JWT_SECRET = os.getenv("SESSION_SECRET", "tigo-leads-secret-change-in-prod")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 10

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ─── Apps Script ─────────────────────────────────────────
def verify_apps_script_key(x_api_key: str = Header(...)):
    """Authenticate inbound Apps Script payloads."""
    if not APPS_SCRIPT_KEY or x_api_key != APPS_SCRIPT_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


# ─── Session tokens (JWT) ────────────────────────────────
def create_session_token(email: str, role: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(
        {"sub": email, "role": role, "exp": expire},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM
    )


def decode_session_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


def require_session(session: str = Cookie(default=None)):
    """FastAPI dependency: redirect to login if no valid session cookie."""
    payload = decode_session_token(session) if session else None
    if not payload:
        raise HTTPException(status_code=307, headers={"Location": "/"})
    return payload


# ─── PIN hashing (bcrypt via passlib) ────────────────────
def hash_pin(pin: str) -> str:
    return _pwd_ctx.hash(pin)


def check_pin(plain: str, stored: str) -> bool:
    """Verify a PIN. Auto-handles legacy plain-text PINs."""
    if stored.startswith("$2"):  # bcrypt hash
        return _pwd_ctx.verify(plain, stored)
    return plain == stored  # legacy plain text


# ─── Admin PIN dependency ────────────────────────────────
def verify_admin_pin(x_admin_pin: str = Header(None)):
    """Protect admin write endpoints. Sends X-Admin-Pin header after verify-pin."""
    from utils.settings import get_setting
    stored = get_setting("admin_pin", "2777")
    if not x_admin_pin or not check_pin(x_admin_pin, stored):
        raise HTTPException(status_code=403, detail="PIN de administrador requerido")
