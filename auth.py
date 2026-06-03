"""
auth.py — API key and token authentication helpers
"""
import os
from fastapi import Header, HTTPException

APPS_SCRIPT_KEY = os.getenv("APPS_SCRIPT_KEY", "")

def verify_apps_script_key(x_api_key: str = Header(...)):
    """Used by Apps Script endpoints to authenticate inbound lead payloads."""
    if not APPS_SCRIPT_KEY or x_api_key != APPS_SCRIPT_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


def verify_admin_pin(x_admin_pin: str = Header(None)):
    """Protect admin write endpoints. Frontend must send X-Admin-Pin header after verify-pin."""
    from utils.settings import get_setting
    correct_pin = get_setting("admin_pin", "2777")
    if not x_admin_pin or x_admin_pin != correct_pin:
        raise HTTPException(status_code=403, detail="PIN de administrador requerido")
