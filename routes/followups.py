"""
routes/followups.py — Followup management (SEGUIMIENTO leads)
"""
from fastapi import APIRouter
from database import execute
from datetime import datetime, timezone

router = APIRouter()


@router.get("")
def get_followups(email: str):
    """Return all SEGUIMIENTO leads for the given agent."""
    from utils.logic import get_now
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
    """Re-assign a SEGUIMIENTO lead back to the agent."""
    execute(
        """
        UPDATE leads
        SET estado = 'ASIGNADO',
            agente = %s,
            updated_at = now()
        WHERE message_id = %s AND estado = 'SEGUIMIENTO'
        """,
        (email, message_id)
    )
    return {"success": True}
