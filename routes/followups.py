"""
routes/followups.py — Followup management (SEGUIMIENTO leads)
"""
from fastapi import APIRouter
from database import execute
from datetime import datetime, timezone
from utils.logic import get_now

router = APIRouter()


@router.get("")
def get_followups(email: str):
    """Return all SEGUIMIENTO leads for the given agent."""
    now = get_now()
    rows = execute(
        """
        SELECT message_id, nombre, linea, plan, rellamar_en,
               agente_original, reagendar_tipo, nocontacto_intentos,
               (rellamar_en <= %s) AS due_now
        FROM leads
        WHERE agente_original = %s
          AND estado = 'SEGUIMIENTO'
          AND rellamar_en IS NOT NULL
        ORDER BY rellamar_en ASC
        """,
        (now, email),
        fetch=True
    )
    return {"success": True, "items": rows}


@router.post("/take")
def take_followup(message_id: str, email: str):
    """Re-assign a SEGUIMIENTO lead back to the agent (parity with apiTakeFollowup)."""
    now = get_now()
    execute(
        """
        UPDATE leads
        SET estado = 'ASIGNADO',
            agente = %s,
            agente_original = %s,
            fecha_asignacion = %s,
            seguimiento_tomado_por = %s,
            seguimiento_tomado_en = %s,
            updated_at = now()
        WHERE message_id = %s AND estado = 'SEGUIMIENTO'
        """,
        (email, email, now, email, now, message_id)
    )
    # Update agent's last_seen (not last_assigned, to preserve queue priority)
    execute(
        "UPDATE agents SET last_seen = %s, updated_at = %s WHERE email = %s",
        (now, now, email)
    )
    return {"success": True}
