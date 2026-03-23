"""
routes/coordinator.py — Coordinator dashboard data
"""
from fastapi import APIRouter
from database import execute, fetchone

router = APIRouter()


@router.get("/dashboard")
def get_dashboard():
    """Return live stats: queue, agents, recent leads."""
    queue = fetchone(
        "SELECT COUNT(*) AS total FROM leads WHERE estado = 'NUEVO' AND agente IS NULL"
    )
    agents = execute(
        """
        SELECT a.email, a.estado, a.last_seen, a.max_leads,
               COUNT(l.id) FILTER (WHERE l.estado = 'ASIGNADO') AS open_leads
        FROM agents a
        LEFT JOIN leads l ON l.agente = a.email
        GROUP BY a.email, a.estado, a.last_seen, a.max_leads
        ORDER BY a.email
        """,
        fetch=True
    )
    recent = execute(
        """
        SELECT message_id, nombre, linea, plan, estado, agente, fecha_gmail, fecha_asignacion
        FROM leads
        ORDER BY created_at DESC
        LIMIT 50
        """,
        fetch=True
    )
    return {
        "success": True,
        "queueCount": queue["total"] if queue else 0,
        "agents": agents,
        "recentLeads": recent
    }


@router.post("/release/{message_id}")
def release_lead(message_id: str):
    """Release a lead back to the queue (coordinator action)."""
    execute(
        """
        UPDATE leads
        SET estado = 'NUEVO', agente = NULL, fecha_asignacion = NULL, updated_at = now()
        WHERE message_id = %s
        """,
        (message_id,)
    )
    return {"success": True}
