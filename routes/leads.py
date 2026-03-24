"""
routes/leads.py — Lead management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from models import LeadCreate, LeadStatusUpdate, LeadOut, ResponseOK, LeadRelease
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
    from utils.logic import get_phone_suffix
    
    # 1. Message ID Check
    existing = fetchone(
        "SELECT id FROM leads WHERE message_id = %s",
        (lead.message_id,)
    )
    if existing:
        return {"success": True, "message": "Lead already exists", "id": str(existing["id"])}
    
    # 2. Phone Suffix Check (Deduplication)
    suffix = get_phone_suffix(lead.linea)
    if suffix:
        # Check for other leads with same suffix created today
        dup = fetchone(
            "SELECT id, message_id FROM leads WHERE RIGHT(linea, 8) = %s AND created_at > now() - interval '24 hours' LIMIT 1",
            (suffix,)
        )
        if dup:
             logger.info(f"Duplicate phone detected: {suffix} matching {dup['message_id']}")

    execute(
        """
        INSERT INTO leads (
            message_id, nombre, linea, plan, fecha_gmail, tracking, gaid,
            origen, url, equipo, utm, horario, timestamp_sheet,
            documento, compania, operacion, tsource, modal, direccion, email
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            lead.message_id, lead.nombre, lead.linea, lead.plan, lead.fecha_gmail, lead.tracking, lead.gaid,
            lead.origen, lead.url, lead.equipo, lead.utm, lead.horario, lead.timestamp_sheet,
            lead.documento, lead.compania, lead.operacion, lead.tsource, lead.modal, lead.direccion, lead.email
        )
    )

    # Try auto-assign immediately
    res = auto_assign.run()
    logger.info(f"Auto-assign result for {lead.message_id}: {res}")

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
    lead = fetchone("SELECT * FROM leads WHERE message_id = %s", (message_id,))
    if not lead:
        raise HTTPException(404, "Lead not found")

    # 1. No Contact Logic Parity
    nocontacto = body.nocontacto_intentos if body.nocontacto_intentos is not None else lead.get("nocontacto_intentos", 0)
    estado = body.estado
    
    if nocontacto >= 3 and estado == "SEGUIMIENTO":
        # Force close as No Venta -> Límite de intentos reached
        estado = "CERRADO"
        logger.info(f"Forcing closure of {message_id} due to 3 no-contact attempts")

    execute(
        """
        UPDATE leads
        SET estado = %s,
            resultado = COALESCE(%s, resultado),
            rellamar_en = %s, -- Overwrite if provided, null if clearing
            reagendar_tipo = COALESCE(%s, reagendar_tipo),
            nocontacto_intentos = %s,
            tip_tipo = COALESCE(%s, tip_tipo),
            tip_resultado = COALESCE(%s, tip_resultado),
            tip_motivo = COALESCE(%s, tip_motivo),
            tip_submotivo = COALESCE(%s, tip_submotivo),
            updated_at = now()
        WHERE message_id = %s
        """,
        (
            estado,
            body.resultado,
            body.rellamar_en,
            body.reagendar_tipo,
            nocontacto,
            body.tip_tipo,
            body.tip_resultado,
            body.tip_motivo,
            body.tip_submotivo,
            message_id
        )
    )
    return {"success": True}


@router.post("/{message_id}/release")
def release_lead(message_id: str, body: LeadRelease, email: str):
    """
    Release an assigned lead (legacy parity).
    - If email matches current agent: OK.
    - If not, check if owner is OFFLINE or inactive (> 3 min).
    """
    lead = fetchone("SELECT agente, estado FROM leads WHERE message_id = %s", (message_id,))
    if not lead:
        raise HTTPException(404, "Lead not found")
    
    if lead["estado"] != "ASIGNADO":
        raise HTTPException(400, "Solo se pueden liberar leads en estado ASIGNADO.")
    
    assigned_to = lead["agente"]
    if not assigned_to:
        return {"success": True} # Already released

    can_release = False
    if assigned_to == email:
        can_release = True
    else:
        # Check owner status
        owner = fetchone("SELECT estado, last_seen FROM agents WHERE email = %s", (assigned_to,))
        if not owner:
            can_release = True
        else:
            is_offline = owner["estado"] == "OFFLINE"
            last_seen = owner["last_seen"]
            if last_seen and last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            
            inactive = (datetime.now(timezone.utc) - last_seen).total_seconds() > 180
            if is_offline or inactive:
                can_release = True
            
    if not can_release:
        raise HTTPException(403, f"No puedes liberar este lead. Pertenece a {assigned_to} y está activo.")
    
    execute(
        """
        UPDATE leads
        SET estado = 'NUEVO',
            agente = NULL,
            fecha_asignacion = NULL,
            liberado_por = %s,
            liberado_en = now(),
            liberado_motivo = %s,
            updated_at = now()
        WHERE message_id = %s
        """,
        (email, body.motivo, message_id)
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


@router.get("/stats")
def get_agent_stats(email: str):
    """Return sidebar stats for the given agent."""
    # 1. Leads en cola
    queue = fetchone("SELECT COUNT(*) AS total FROM leads WHERE estado = 'NUEVO' AND agente IS NULL")
    
    # 2. Mis pendientes (Activos)
    mine = fetchone("SELECT COUNT(*) AS total FROM leads WHERE agente = %s AND estado = 'ASIGNADO'", (email,))
    
    # 3. Fuera de SLA (> 5 min en cola o > 15 min sin gestión)
    sla = fetchone(
        """
        SELECT COUNT(*) AS total FROM leads 
        WHERE (estado = 'NUEVO' AND created_at < now() - interval '5 minutes')
           OR (estado = 'ASIGNADO' AND agente = %s AND updated_at < now() - interval '15 minutes')
        """, 
        (email,)
    )
    
    # 4. Seguimientos hoy
    followups = fetchone(
        "SELECT COUNT(*) AS total FROM leads WHERE agente = %s AND estado = 'SEGUIMIENTO' AND (rellamar_en::date = now()::date OR rellamar_en IS NULL)",
        (email,)
    )
    
    # 5. Mis ventas hoy
    sales = fetchone("SELECT COUNT(*) AS total FROM sales WHERE agente = %s AND created_at::date = now()::date", (email,))

    return {
        "success": True,
        "queue": queue["total"] if queue else 0,
        "pendientes": mine["total"] if mine else 0,
        "sla": sla["total"] if sla else 0,
        "followups": followups["total"] if followups else 0,
        "sales_today": sales["total"] if sales else 0
    }
