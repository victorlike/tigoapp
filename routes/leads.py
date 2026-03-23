"""
routes/leads.py — Lead management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from models import LeadCreate, LeadStatusUpdate, LeadOut, ResponseOK
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


# ─── POST /api/leads/bulk  ─────────────────────────────
@router.post("/bulk", dependencies=[Depends(verify_apps_script_key)])
def bulk_create_leads(leads: list[LeadOut]):
    """Bulk import leads. Used for migration."""
    if not leads: return {"success": True, "count": 0}
    
    # We use a raw SQL for performance
    query = """
    INSERT INTO leads (
        message_id, nombre, linea, plan, estado, agente, agente_original,
        fecha_gmail, fecha_asignacion, resultado, rellamar_en,
        reagendar_tipo, nocontacto_intentos, created_at, updated_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    ON CONFLICT (message_id) DO NOTHING
    """
    params = [
        (
            l.message_id, l.nombre, l.linea, l.plan, l.estado, l.agente, l.agente_original,
            l.fecha_gmail, l.fecha_asignacion, l.resultado, l.rellamar_en,
            l.reagendar_tipo, l.nocontacto_intentos, l.created_at or datetime.now(), l.updated_at or datetime.now()
        )
        for l in leads
    ]
    
    conn = database.get_conn()
    try:
        with conn.cursor() as cur:
            cur.executemany(query, params)
            conn.commit()
    finally:
        database.release_conn(conn)
        
    return {"success": True, "count": len(leads)}
