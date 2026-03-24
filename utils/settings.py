"""
utils/settings.py — Helper to fetch global system settings with elementary caching
"""
import time
from database import fetchone

_cache = {}
_last_fetch = 0
CACHE_TTL = 30  # 30 seconds

def get_setting(key: str, default: str = None) -> str:
    """Fetch a setting from the database with a 30s cache."""
    global _last_fetch, _cache
    now = time.time()
    
    if now - _last_fetch > CACHE_TTL:
        try:
            from database import execute
            rows = execute("SELECT key, value FROM settings")
            _cache = {r['key']: r['value'] for r in rows}
            _last_fetch = now
        except Exception as e:
            print(f"Error fetching settings: {e}")
            return default

    return _cache.get(key, default)

def get_int_setting(key: str, default: int = 0) -> int:
    try:
        return int(get_setting(key, str(default)))
    except:
        return default
