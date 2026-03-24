"""
routes/admin.py — Administrator endpoints for role management and system settings
"""
from database import execute, fetchone
from auth import verify_apps_script_key
from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any

router = APIRouter()

# ─── Schema Migration (Lazy) ───────────────────────────────
def migrate_admin_schema():
    """Ensure the agents table has 'role' and the settings table exists."""
    try:
        execute("ALTER TABLE agents ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'AGENT';")
        execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(50) PRIMARY KEY,
                value VARCHAR(255),
                updated_at TIMESTAMP DEFAULT now()
            );
        """)
        # Default settings
        execute("INSERT INTO settings (key, value) VALUES ('sla_min', '5') ON CONFLICT (key) DO NOTHING;")
        execute("INSERT INTO settings (key, value) VALUES ('stuck_min', '15') ON CONFLICT (key) DO NOTHING;")
        execute("INSERT INTO settings (key, value) VALUES ('auto_assign_enabled', 'true') ON CONFLICT (key) DO NOTHING;")
        print("Admin schema migration completed.")
    except Exception as e:
        print(f"Error migrating admin schema: {e}")

# Migration is now moved to main.py startup for better reliability
# migrate_admin_schema()


# ─── Endpoints ───────────────────────────────────────────
from pydantic import BaseModel

class PinRequest(BaseModel):
    pin: str

@router.post("/verify-pin")
def verify_pin(data: PinRequest):
    """Verify the admin PIN to unlock the dashboard."""
    from utils.settings import get_setting
    correct_pin = get_setting("admin_pin", "1234")
    if data.pin == correct_pin:
        return {"success": True}
    return {"success": False, "error": "PIN incorrecto"}

@router.get("/users")
def get_users():
    """List all agents/users with their roles and capacity."""
    users = execute("""
        SELECT 
            email, 
            estado, 
            role, 
            max_leads,
            last_seen,
            EXTRACT(EPOCH FROM (now() - last_seen))::int as last_seen_ago_sec
        FROM agents
        ORDER BY role DESC, email ASC
    """, fetch=True)
    return {"success": True, "items": users}

@router.post("/users/update")
def update_user(data: Dict[str, Any]):
    """Update role or max_leads for a user."""
    email = data.get("email")
    role = data.get("role")
    max_leads = data.get("max_leads")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    if role:
        execute("UPDATE agents SET role = %s WHERE email = %s", (role.upper(), email))
    if max_leads is not None:
        execute("UPDATE agents SET max_leads = %s WHERE email = %s", (max_leads, email))
        
    return {"success": True}

@router.get("/settings")
def get_settings():
    """Fetch all global system settings."""
    rows = execute("SELECT key, value FROM settings")
    settings = {r['key']: r['value'] for r in rows}
    return {"success": True, "settings": settings}

@router.post("/settings/update")
def update_settings(data: Dict[str, Any]):
    """Update global system settings."""
    for key, value in data.items():
        execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (%s, %s, now()) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()",
            (key, str(value))
        )
    return {"success": True}

@router.get("/audit-logs")
def get_audit_logs():
    """Placeholder for critical action logs."""
    # This could query a separate audit table if implemented
    return {"success": True, "items": []}
