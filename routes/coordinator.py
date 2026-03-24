"""
routes/coordinator.py — Coordinator dashboard data
"""
from database import execute, fetchone
from auth import verify_apps_script_key
from fastapi import APIRouter, Depends
from utils.settings import get_int_setting

router = APIRouter()


@router.get("/dashboard")
def get_dashboard():
    """Return all data for the Coordinator Dashboard tabs."""
    # 1. Agents (Torre de Control)
    agents = execute(
        """
        SELECT 
            email, estado, last_seen, max_leads, last_assigned,
            (SELECT COUNT(*) FROM leads WHERE leads.agente = agents.email AND leads.estado = 'ASIGNADO') as open_leads,
            EXTRACT(EPOCH FROM (now() - last_seen))::int as last_seen_ago_sec,
            EXTRACT(EPOCH FROM (now() - last_assigned))::int as last_assigned_ago_sec
        FROM agents
        ORDER BY estado DESC, last_seen DESC
        """,
        fetch=True
    )

    # 2. Stuck Leads (ASIGNADO > 15 min)
    stuck_min = get_int_setting("stuck_min", 15)
    stuck_leads = execute(
        f"""
        SELECT 
            message_id, linea, nombre, agente,
            EXTRACT(EPOCH FROM (now() - fecha_asignacion))/60 as minutos_asignado
        FROM leads 
        WHERE estado = 'ASIGNADO' AND fecha_asignacion < now() - interval '{stuck_min} minutes'
        ORDER BY minutos_asignado DESC
        """,
        fetch=True
    )

    # 3. Seguimientos (Today)
    seguimientos = execute(
        """
        SELECT * FROM leads 
        WHERE estado = 'SEGUIMIENTO' 
          AND (rellamar_en::date <= now()::date OR rellamar_en IS NULL) 
        ORDER BY rellamar_en ASC
        """,
        fetch=True
    )

    # 4. Backoffice (Pending Sales)
    backoffice = execute(
        """
        SELECT * FROM sales 
        WHERE backoffice_status IS NULL OR backoffice_status = 'Pendiente de carga' 
        ORDER BY created_at ASC
        """,
        fetch=True
    )

    # 5. KPIs
    # Today's stats
    kpi_queue = fetchone("SELECT COUNT(*) as total FROM leads WHERE estado = 'NUEVO'")
    kpi_sales = fetchone("SELECT COUNT(*) as total FROM sales WHERE created_at::date = now()::date")
    kpi_approved = fetchone("SELECT COUNT(*) as total FROM sales WHERE backoffice_status = 'OK' AND backoffice_at::date = now()::date")
    kpi_nosale = fetchone("SELECT COUNT(*) as total FROM leads WHERE resultado = 'No Venta' AND updated_at::date = now()::date")
    
    # SLA Breach (NUEVO > 5 min)
    sla_min = get_int_setting("sla_min", 5)
    kpi_sla = fetchone(f"SELECT COUNT(*) as total FROM leads WHERE estado = 'NUEVO' AND created_at < now() - interval '{sla_min} minutes'")

    # 6. Sales by agent and product (Including SEGUIMIENTO breakdown)
    detailed_sales = execute(
        """
        SELECT 
            s.agente, s.producto, s.backoffice_status, s.backoffice_at,
            (SELECT COUNT(*) FROM leads l WHERE l.message_id = s.message_id AND l.resultado = 'Seguimiento') > 0 as is_seguimiento
        FROM sales s
        WHERE s.created_at::date = now()::date
        """,
        fetch=True
    )
    
    sales_by_agent = {}
    sales_by_product = {}
    sales_by_agent_seg = {}
    sales_by_product_seg = {}
    ventas_seg_hoy = 0
    
    for s in detailed_sales:
        ag = s["agente"] or "Sin agente"
        pr = s["producto"] or "Sin producto"
        is_seg = s["is_seguimiento"]
        
        sales_by_agent[ag] = sales_by_agent.get(ag, 0) + 1
        sales_by_product[pr] = sales_by_product.get(pr, 0) + 1
        
        if is_seg:
            ventas_seg_hoy += 1
            sales_by_agent_seg[ag] = sales_by_agent_seg.get(ag, 0) + 1
            sales_by_product_seg[pr] = sales_by_product_seg.get(pr, 0) + 1

    # Calculate conversion
    total_new = kpi_queue["total"] if kpi_queue else 0
    total_sales = kpi_sales["total"] if kpi_sales else 0
    conversion = round((total_sales / total_new * 100), 1) if total_new > 0 else 0

    from datetime import datetime
    return {
        "success": True,
        "agents": agents,
        "stuckLeads": stuck_leads,
        "seguimientos": seguimientos,
        "backofficePending": backoffice,
        "kpis": {
            "queueNew": total_new,
            "ventasCantadasHoy": total_sales,
            "ventasSeguimientoHoy": ventas_seg_hoy,
            "aprobadasPorBOHoy": kpi_approved["total"] if kpi_approved else 0,
            "noVentasHoy": kpi_nosale["total"] if kpi_nosale else 0,
            "salesByAgent": sales_by_agent,
            "salesByProduct": sales_by_product,
            "salesByAgentSeguimiento": sales_by_agent_seg,
            "salesByProductSeguimiento": sales_by_product_seg,
            "conversion": conversion,
            "slaBreached": kpi_sla["total"] if kpi_sla else 0,
            "followupsToday": len(seguimientos),
            "pendingInBackoffice": len(backoffice)
        },
        "serverNow": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


@router.post("/agents/{email}/force-offline")
def force_offline(email: str):
    """Force an agent to OFFLINE status."""
    execute(
        "UPDATE agents SET estado = 'OFFLINE', updated_at = now() WHERE email = %s",
        (email,)
    )
    return {"success": True}


@router.post("/agents/{email}/rescue-all")
def rescue_all_leads(email: str):
    """Release all ASIGNADO leads from an agent back to NUEVO."""
    execute(
        """
        UPDATE leads 
        SET estado = 'NUEVO', 
            agente = NULL, 
            fecha_asignacion = NULL,
            liberado_por = 'COORDINADOR',
            liberado_en = now(),
            liberado_motivo = 'Rescate Masivo'
        WHERE agente = %s AND estado = 'ASIGNADO'
        """,
        (email,)
    )
    return {"success": True}


@router.post("/agents/{email}/force-offline-and-rescue")
def force_offline_and_rescue(email: str):
    """Combined action: force agent OFFLINE and rescue all their leads."""
    execute("UPDATE agents SET estado = 'OFFLINE', updated_at = now() WHERE email = %s", (email,))
    execute(
        """
        UPDATE leads 
        SET estado = 'NUEVO', 
            agente = NULL, 
            fecha_asignacion = NULL,
            liberado_por = 'COORDINADOR',
            liberado_en = now(),
            liberado_motivo = 'Rescate Masivo (Offline Force)'
        WHERE agente = %s AND estado = 'ASIGNADO'
        """,
        (email,)
    )
    return {"success": True}


@router.post("/assign")
def assign_manual(message_id: str, agent_email: str):
    """Manually assign a lead to an agent."""
    execute(
        """
        UPDATE leads
        SET estado = 'ASIGNADO', agente = %s, fecha_asignacion = now(), updated_at = now()
        WHERE message_id = %s
        """,
        (agent_email, message_id)
    )
    # Also update agent's last_assigned
    execute(
        "UPDATE agents SET last_assigned = now(), updated_at = now() WHERE email = %s",
        (agent_email,)
    )
    return {"success": True}


@router.post("/backoffice/approve")
def approve_sale(message_id: str, note: str = ""):
    """Approve a sale in backoffice."""
    execute(
        """
        UPDATE sales
        SET backoffice_status = 'OK', backoffice_notas = %s, backoffice_at = now()
        WHERE message_id = %s
        """,
        (note, message_id)
    )
    return {"success": True}


@router.post("/backoffice/reject")
def reject_sale(message_id: str, note: str = ""):
    """Reject a sale in backoffice."""
    execute(
        """
        UPDATE sales
        SET backoffice_status = 'Rechazado', backoffice_notas = %s, backoffice_at = now()
        WHERE message_id = %s
        """,
        (note, message_id)
    )
    return {"success": True}


@router.post("/release/{message_id}")
def release_lead(message_id: str, motivo: str = "Rescate (coord)"):
    """Release a lead back to the queue (coordinator action)."""
    execute(
        """
        UPDATE leads
        SET estado = 'NUEVO', agente = NULL, fecha_asignacion = NULL, 
            liberado_por = 'COORDINADOR', liberado_en = now(), 
            liberado_motivo = %s, updated_at = now()
        WHERE message_id = %s
        """,
        (motivo, message_id)
    )
    return {"success": True}


@router.post("/close/{message_id}")
def close_lead_coord(message_id: str, motivo: str = "Cierre (coord)"):
    """Force close a lead (e.g. duplicate)."""
    execute(
        """
        UPDATE leads
        SET estado = 'CERRADO', resultado = 'No Venta', 
            tip_tipo = 'No Venta', tip_resultado = 'Duplicado',
            tip_motivo = %s, updated_at = now()
        WHERE message_id = %s
        """,
        (motivo, message_id)
    )
    return {"success": True}


@router.get("/agents/{email}/leads")
def get_agent_leads(email: str):
    """Get list of active leads for a specific agent."""
    rows = execute(
        """
        SELECT message_id, nombre, linea, plan, fecha_asignacion,
               EXTRACT(EPOCH FROM (now() - fecha_asignacion))::int / 60 as minutos_asignado,
               estado
        FROM leads
        WHERE agente = %s AND estado = 'ASIGNADO'
        ORDER BY fecha_asignacion ASC
        """,
        (email,),
        fetch=True
    )
    return {"success": True, "items": rows}


@router.get("/eligible-agents")
def get_eligible_agents():
    """List agents ready to receive a manual assignment (Followup)."""
    rows = execute(
        """
        SELECT 
            email, max_leads,
            (SELECT COUNT(*) FROM leads WHERE leads.agente = agents.email AND leads.estado = 'ASIGNADO') as open_leads
        FROM agents
        WHERE estado = 'ACTIVO' AND last_seen > now() - interval '90 seconds'
        ORDER BY email ASC
        """,
        fetch=True
    )
    # Filter only those with capacity
    eligible = [a for a in rows if a["open_leads"] < a["max_leads"]]
    return {"success": True, "items": eligible}

@router.post("/followups/auto-assign")
def auto_assign_followup(message_id: str, motivo: str = "Auto-asignación (coord)"):
    """Auto-assign a followup lead to the 'best' available agent."""
    rows = execute(
        """
        SELECT 
            email, max_leads,
            (SELECT COUNT(*) FROM leads WHERE leads.agente = agents.email AND leads.estado = 'ASIGNADO') as open_leads
        FROM agents
        WHERE estado = 'ACTIVO' AND last_seen > now() - interval '90 seconds'
        ORDER BY open_leads ASC, email ASC
        """,
        fetch=True
    )
    eligible = [a for a in rows if a["open_leads"] < a["max_leads"]]
    if not eligible:
        return {"success": False, "message": "No hay agentes elegibles (ACTIVO + conectado + cupo)."}
    
    best_agent = eligible[0]["email"]
    return assign_followup_to_agent(message_id, best_agent, motivo)


@router.post("/followups/assign")
def assign_followup_to_agent(message_id: str, agent_email: str, motivo: str = "Asignación manual (coord)"):
    """Manually assign a followup lead to a specific agent."""
    execute(
        """
        UPDATE leads
        SET estado = 'ASIGNADO', agente = %s, fecha_asignacion = now(), 
            seguimiento_tomado_por = %s, seguimiento_tomado_en = now(),
            updated_at = now()
        WHERE message_id = %s AND estado = 'SEGUIMIENTO'
        """,
        (agent_email, agent_email, message_id)
    )
    execute(
        "UPDATE agents SET last_assigned = now(), updated_at = now() WHERE email = %s",
        (agent_email,)
    )
    return {"success": True}

@router.post("/clean", dependencies=[Depends(verify_apps_script_key)])
def clean_database():
    """TRUNCATE all main tables for a fresh start AND ensure schema updates."""
    # 1. Comprehensive self-healing migration for sales table
    columns = [
        "cliente_vendedor", "cliente_nacimiento", "cliente_telefono", "dir_loc", "dir_tipo",
        "dir_esq1", "dir_esq2", "venta_vigencia", "venta_clc", "venta_llevaequipo",
        "venta_precio", "venta_cuotas", "dg_solicita", "dg_importe", "dg_corresponde",
        "envio_tipo", "envio_detalles", "cobro_importe", "cobro_motivo", "cobro_linkemail",
        "link_enviado", "nombre_link", "plateran_cargado", "plateran_so", "estado_pedido",
        "controldoc_subido", "controldoc_estado", "porta_nip", "vendedor_comentarios_por",
        "backoffice_sub_status", "backoffice_agent", "valor_plan", "valor_telefono",
        "revenue", "revenuedolar", "suptipo_reco", "tipo_venta_original"
    ]
    for col in columns:
        execute(f"ALTER TABLE sales ADD COLUMN IF NOT EXISTS {col} TEXT")
    
    # Timestamptz columns
    ts_columns = ["vendedor_comentarios_at", "bo_email_enviado_at", "backoffice_at"]
    for col in ts_columns:
        execute(f"ALTER TABLE sales ADD COLUMN IF NOT EXISTS {col} TIMESTAMPTZ")

    # 2. Cleanup
    for table in ["leads", "sales", "agents"]:
        execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
    return {"success": True, "message": "Database cleaned and schema updated"}
