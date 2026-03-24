"""
routes/leads.py — Lead management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from models import LeadCreate, LeadStatusUpdate, LeadOut, ResponseOK
from database import execute, fetchone
from auth import verify_apps_script_key
import auto_assign
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

OPEN_STATES = {"ASIGNADO", "SEGUIMIENTO"}


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
        INSERT INTO leads (message_id, nombre, linea, plan, fecha_gmail, tracking, gaid)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (lead.message_id, lead.nombre, lead.linea, lead.plan, lead.fecha_gmail, lead.tracking, lead.gaid)
    )

    # Try auto-assign immediately
    auto_assign.run()

    return {"success": True, "message": "Lead created"}


# ─── GET /api/leads/mine?email=...  ────────────────────
@router.get("/mine")
def get_my_leads(email: str):
    """Return categorized leads and sales for the given agent."""
    # 1. Active Leads (ASIGNADO)
    active = execute(
        "SELECT * FROM leads WHERE agente = %s AND estado = 'ASIGNADO' ORDER BY fecha_asignacion ASC",
        (email,),
        fetch=True
    )
    
    # 2. Seguimientos (SEGUIMIENTO)
    followups = execute(
        "SELECT * FROM leads WHERE agente = %s AND estado = 'SEGUIMIENTO' ORDER BY rellamar_en ASC",
        (email,),
        fetch=True
    )
    
    # 3. Mis Ventas (RESULTADO = Venta)
    sales = execute(
        "SELECT * FROM sales WHERE agente = %s ORDER BY created_at DESC LIMIT 50",
        (email,),
        fetch=True
    )
    
    # 4. Backoffice (Sales from this agent and their state)
    backoffice = execute(
        "SELECT message_id, producto, cliente_nombre, backoffice_status, backoffice_notas FROM sales WHERE agente = %s AND backoffice_status != 'Aprobado' ORDER BY updated_at DESC",
        (email,),
        fetch=True
    )

    return {
        "success": True,
        "active": active,
        "followups": followups,
        "sales": sales,
        "backoffice": backoffice
    }


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
            tip_tipo = COALESCE(%s, tip_tipo),
            tip_resultado = COALESCE(%s, tip_resultado),
            tip_motivo = COALESCE(%s, tip_motivo),
            tip_submotivo = COALESCE(%s, tip_submotivo),
            updated_at = now()
        WHERE message_id = %s
        """,
        (
            body.estado,
            body.resultado,
            body.rellamar_en,
            body.reagendar_tipo,
            body.nocontacto_intentos,
            body.tip_tipo,
            body.tip_resultado,
            body.tip_motivo,
            body.tip_submotivo,
            message_id
        )
    )
    return {"success": True}


# ─── POST /api/leads/bulk  ─────────────────────────────
@router.post("/bulk", dependencies=[Depends(verify_apps_script_key)])
def bulk_create_leads(leads: list[LeadOut]):
    """Bulk import leads."""
    if not leads: return {"success": True, "count": 0}
    
    logger.info(f"Bulk importing {len(leads)} leads")
    
    query = """
    INSERT INTO leads (
        message_id, nombre, linea, plan, estado, agente, agente_original,
        fecha_gmail, fecha_asignacion, resultado, rellamar_en,
        reagendar_tipo, nocontacto_intentos, sla_asignacion,
        tip_tipo, tip_resultado, tip_motivo, tip_submotivo,
        tracking, gaid, cantidad_ventas,
        origen, url, equipo, utm, horario, timestamp_sheet, documento,
        compania, operacion, tsource, modal, direccion, email,
        fecha_cierre, notas, minutos_asignacion, seguimiento_tomado_por,
        seguimiento_tomado_en, liberado_por, liberado_en, liberado_motivo, error
    ) VALUES (
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
    )
    ON CONFLICT (message_id) DO UPDATE SET
        estado = EXCLUDED.estado,
        agente = EXCLUDED.agente,
        resultado = EXCLUDED.resultado,
        tip_resultado = EXCLUDED.tip_resultado,
        tracking = EXCLUDED.tracking,
        gaid = EXCLUDED.gaid,
        updated_at = now()
    """
    params = [
        (
            l.message_id, l.nombre, l.linea, l.plan, l.estado, l.agente, l.agente_original,
            l.fecha_gmail, l.fecha_asignacion, l.resultado, l.rellamar_en,
            l.reagendar_tipo, l.nocontacto_intentos, l.sla_asignacion,
            l.tip_tipo, l.tip_resultado, l.tip_motivo, l.tip_submotivo,
            l.tracking, l.gaid, l.cantidad_ventas,
            l.origen, l.url, l.equipo, l.utm, l.horario, l.timestamp_sheet, l.documento,
            l.compania, l.operacion, l.tsource, l.modal, l.direccion, l.email,
            l.fecha_cierre, l.notas, l.minutos_asignacion, l.seguimiento_tomado_por,
            l.seguimiento_tomado_en, l.liberado_por, l.liberado_en, l.liberado_motivo, l.error
        )
        for l in leads
    ]
    
    from database import bulk_execute
    bulk_execute(query, params)
    
    return {"success": True, "count": len(leads)}
