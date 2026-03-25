"""
utils/logic.py — Standardized business logic for LeadDesk/Tigo Parity
"""
from datetime import datetime, timedelta
import re

def normalize_product_group(product_name: str) -> str:
    """
    Standardize product group names into:
    ALTAS | RECOS | MIGRAS | UPSELLINGS
    """
    p = str(product_name or "").strip().upper()
    
    # Altas / Porta
    if any(x in p for x in ["ALTA", "PORTA"]):
        return "ALTAS"
    
    # Recos
    if any(x in p for x in ["RECO", "RECONTRATO"]):
        return "RECOS"
    
    # Migras
    if any(x in p for x in ["MIGRA", "MIGRACIÓN"]):
        return "MIGRAS"
    
    # Upsellings
    if any(x in p for x in ["UPSELL", "UPGRADE", "UPSELLING"]):
        return "UPSELLINGS"
    
    return "ALTAS" # Fallback

def get_phone_suffix(phone: str) -> str:
    """Extract last 8 digits of a phone number for deduplication."""
    digits = re.sub(r"\D", "", str(phone or ""))
    return digits[-8:] if len(digits) >= 8 else digits

def is_within_timeframe(t1: datetime, t2: datetime, seconds: int = 60) -> bool:
    """Check if two datetimes are within X seconds of each other."""
    if not t1 or not t2: return False
    return abs((t1 - t2).total_seconds()) <= seconds

def get_now() -> datetime:
    """Return current time in America/Montevideo timezone."""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("America/Montevideo"))
