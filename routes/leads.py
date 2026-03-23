"""
routes/leads.py — Lead management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from models import LeadCreate, LeadStatusUpdate, ResponseOK
from database import execute, fetchone
from auth import verify_apps_script_key
import auto_assign

router = APIRouter()

OPEN_STATES = {"ASIGNADO", "EN CURSO"}


# ─── POST /api/leads  (called by Apps Script) ──────────
@router.post("", dependencies=[Depends(verify_apps_script_key)])
def create_lead(lead: LeadCreate):
    """Create a new lead from Gmail. Called by Apps Script."""
    existing = fetchone(
        "SELECT id FROM leads WHERE message_id = %s",
        (lead.message_id,)
    )
    if existing:
        return {"success": True, "message": "Lead already exists", "id": str(existing["id"])}

    execute(
        """
        INSERT INTO leads (message_id, nombre, linea, plan, fecha_gmail)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (lead.message_id, lead.nombre, lead.linea, lead.plan, lead.fecha_gmail)
    )

    # Try auto-assign immediately
    auto_assign.run()

    return {"success": True, "message": "Lead created"}


# ─── GET /api/leads/mine?email=...  ────────────────────
@router.get("/mine")
def get_my_leads(email: str):
    """Return all open leads assigned to the given agent."""
    rows = execute(
        """
        SELECT * FROM leads
        WHERE agente = %s AND estado = ANY(%s::text[])
        ORDER BY fecha_asignacion ASC
        """,
        (email, list(OPEN_STATES)),
        fetch=True
    )
    return {"success": True, "leads": rows}


# ─── GET /api/leads/queue  ─────────────────────────────
@router.get("/queue")
def get_queue():
    """Return count of unassigned leads."""
    row = fetchone(
        "SELECT COUNT(*) AS total FROM leads WHERE estado = 'NUEVO' AND agente IS NULL"
    )
    return {"success": True, "count": row["total"] if row else 0}


# ─── PATCH /api/leads/{message_id}/status  ─────────────
@router.patch("/{message_id}/status")
def update_lead_status(message_id: str, body: LeadStatusUpdate):
    """Update lead estado, resultado, rellamar_en, etc."""
    lead = fetchone("SELECT id FROM leads WHERE message_id = %s", (message_id,))
    if not lead:
        raise HTTPException(404, "Lead not found")

    execute(
        """
        UPDATE leads
        SET estado = %s,
            resultado = COALESCE(%s, resultado),
            rellamar_en = COALESCE(%s, rellamar_en),
            reagendar_tipo = COALESCE(%s, reagendar_tipo),
            nocontacto_intentos = COALESCE(%s, nocontacto_intentos),
            updated_at = now()
        WHERE message_id = %s
        """,
        (
            body.estado,
            body.resultado,
            body.rellamar_en,
            body.reagendar_tipo,
            body.nocontacto_intentos,
            message_id
        )
    )
    return {"success": True}


# ─── GET /api/leads/{message_id}  ──────────────────────
@router.get("/{message_id}")
def get_lead(message_id: str):
    lead = fetchone("SELECT * FROM leads WHERE message_id = %s", (message_id,))
    if not lead:
        raise HTTPException(404, "Lead not found")
    return {"success": True, "lead": lead}
