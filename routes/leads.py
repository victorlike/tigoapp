"""
routes/leads.py — Lead management endpoints
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
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
    try:
        res = auto_assign.run()
        logger.info(f"Auto-assign result for {lead.message_id}: {res}")
    except Exception as ae:
        logger.error(f"Auto-assign error during lead creation: {ae}")

    return {"success": True, "message": "Lead created", "message_id": lead.message_id}


# ─── GET /api/leads/mine?email=...  ────────────────────
@router.get("/mine")
def get_my_leads(email: str):
    """Return categorized leads and sales for the given agent."""
    active = execute(
        "SELECT * FROM leads WHERE agente = %s AND estado = 'ASIGNADO' ORDER BY fecha_asignacion ASC",
        (email,),
        fetch=True
    )
    return {"success": True, "myLeads": active}


# ─── GET /api/leads/followups  ─────────────────────────
@router.get("/followups")
def get_followups(email: str):
    """Return scheduled followups for the agent."""
    now = datetime.now()
    items = execute(
        """
        SELECT *, (rellamar_en <= %s) AS due_now 
        FROM leads 
        WHERE agente = %s AND estado = 'SEGUIMIENTO' 
        ORDER BY rellamar_en ASC
        """,
        (now, email),
        fetch=True
    )
    return {"success": True, "items": items}


# ─── GET /api/leads/dup_check  ─────────────────────────
@router.get("/dup_check")
def duplicate_check(phone: str, message_id: str):
    """Check for recent leads with the same phone suffix."""
    from utils.logic import get_phone_suffix
    suffix = get_phone_suffix(phone)
    if not suffix:
        return {"success": True, "today": 0, "items": []}
    
    # Coincidences today (last 24h)
    items = execute(
        """
        SELECT fecha_gmail, agente, estado, resultado 
        FROM leads 
        WHERE RIGHT(linea, 8) = %s 
          AND message_id != %s
          AND created_at > now() - interval '24 hours'
        ORDER BY created_at DESC
        """,
        (suffix, message_id),
        fetch=True
    )
    return {
        "success": True, 
        "today": len(items), 
        "items": items
    }


# ─── GET /api/leads/queue  ─────────────────────────────
@router.get("/queue")
def get_queue():
    """Return count of unassigned leads."""
    row = fetchone(
        "SELECT COUNT(*) AS total FROM leads WHERE estado = 'NUEVO' AND agente IS NULL"
    )
    return {"success": True, "count": row["total"] if row else 0}


# ─── GET /api/leads/{message_id}  ──────────────────────
@router.get("/{message_id}")
def get_lead_details(message_id: str):
    """Return full details for a specific lead or sale."""
    lead = fetchone("SELECT * FROM leads WHERE message_id = %s", (message_id,))
    if lead:
        return {"success": True, "lead": lead}
        
    sale = fetchone("SELECT * FROM sales WHERE message_id = %s", (message_id,))
    if sale:
        return {"success": True, "sale": sale}
        
    raise HTTPException(404, "Lead/Sale not found")


# ─── PATCH /api/leads/{message_id}/status  ─────────────
@router.patch("/{message_id}/status")
def update_lead_status(message_id: str, body: LeadStatusUpdate, background_tasks: BackgroundTasks):
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

    # Handle Sale Data if provided
    if body.sale_data and (estado == "Venta" or body.tip_resultado == "Venta"):
        from routes.sales import create_sale
        from models import SaleCreate
        try:
            # Prepare SaleCreate-compatible data
            s_data = body.sale_data.copy()
            s_data["message_id"] = message_id
            s_data["agente"] = lead["agente"]
            s_data["tip_tipo"] = body.tip_tipo or lead["tip_tipo"]
            s_data["tip_resultado"] = body.tip_resultado or lead["tip_resultado"]
            s_data["tip_motivo"] = body.tip_motivo or lead["tip_motivo"]
            
            # Ensure required fields are present
            if "producto" not in s_data: s_data["producto"] = s_data.get("TipoVenta", "VENTA")
            if "tipo_venta" not in s_data: s_data["tipo_venta"] = s_data.get("TipoVenta", "VENTA")
            
            sale_obj = SaleCreate(**s_data)
            create_sale(sale_obj, background_tasks)
        except Exception as e:
            logger.error(f"Error creating sale from lead status update: {e}")

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
        WHERE (estado = 'NUEVO' AND created_at < now() - interval '5 minutes' AND created_at >= current_date)
           OR (estado = 'ASIGNADO' AND agente = %s AND updated_at < now() - interval '15 minutes' AND updated_at >= current_date)
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
