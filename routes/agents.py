"""
routes/agents.py — Agent presence and status management
"""
from fastapi import APIRouter, HTTPException
from models import AgentStatusUpdate
from database import execute, fetchone
from datetime import datetime, timezone
import auto_assign

router = APIRouter()

CONNECTED_SECONDS = 90
OPEN_STATE = "ASIGNADO"


# ─── POST /api/agent/touch  ────────────────────────────
@router.post("/touch")
def touch_agent(email: str):
    """Update agent LastSeen (heartbeat). Creates agent if not exists."""
    now = datetime.now(timezone.utc)

    existing = fetchone("SELECT email FROM agents WHERE email = %s", (email,))
    if not existing:
        execute(
            """
            INSERT INTO agents (email, estado, last_seen, max_leads, updated_at)
            VALUES (%s, 'OFFLINE', %s, 1, %s)
            """,
            (email, now, now)
        )
    else:
        execute(
            "UPDATE agents SET last_seen = %s, updated_at = %s WHERE email = %s",
            (now, now, email)
        )
    return {"success": True}


# ─── PATCH /api/agent/status  ──────────────────────────
@router.patch("/status")
def set_agent_status(email: str, body: AgentStatusUpdate):
    """Change agent status: ACTIVO or OFFLINE."""
    if body.estado == "OFFLINE":
        # Block OFFLINE if agent has open leads
        row = fetchone(
            "SELECT COUNT(*) AS n FROM leads WHERE agente = %s AND estado = %s",
            (email, OPEN_STATE)
        )
        if row and row["n"] > 0:
            raise HTTPException(
                409,
                detail=f"No puedes desconectarte con {row['n']} lead(s) abierto(s)."
            )

    now = datetime.now(timezone.utc)
    execute(
        "UPDATE agents SET estado = %s, last_seen = %s, updated_at = %s WHERE email = %s",
        (body.estado, now, now, email)
    )

    # If going ACTIVO, try to assign pending leads
    if body.estado == "ACTIVO":
        auto_assign.run()

    return {"success": True, "estado": body.estado}


# ─── GET /api/agent/info  ──────────────────────────────
@router.get("/info")
def get_agent_info(email: str):
    """Return current agent info."""
    agent = fetchone("SELECT * FROM agents WHERE email = %s", (email,))
    if not agent:
        # Auto-create on first access
        touch_agent(email)
        agent = fetchone("SELECT * FROM agents WHERE email = %s", (email,))
    return {"success": True, "agent": agent}


# ─── GET /api/agent/list (coordinator) ─────────────────
@router.get("/list")
def list_agents():
    """List all agents with their current open lead count."""
    rows = execute(
        """
        SELECT a.*,
               COUNT(l.id) FILTER (WHERE l.estado = 'ASIGNADO') AS open_leads
        FROM agents a
        LEFT JOIN leads l ON l.agente = a.email
        GROUP BY a.email
        ORDER BY a.email
        """,
        fetch=True
    )
    return {"success": True, "agents": rows}
