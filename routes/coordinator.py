"""
routes/coordinator.py — Coordinator dashboard data
"""
from database import execute, fetchone
from auth import verify_apps_script_key
from fastapi import APIRouter, Depends

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

    # 2. Stuck Leads (Rescue)
    # Leads assigned for more than 15 minutes
    stuck = execute(
        """
        SELECT *, EXTRACT(EPOCH FROM (now() - fecha_asignacion))::int / 60 as minutos_asignado
        FROM leads
        WHERE estado = 'ASIGNADO'
          AND fecha_asignacion < now() - interval '15 minutes'
        ORDER BY fecha_asignacion ASC
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
    kpi_sla = fetchone("SELECT COUNT(*) as total FROM leads WHERE estado = 'NUEVO' AND created_at < now() - interval '5 minutes'")

    # Sales by agent
    sales_by_agent = execute(
        "SELECT agente, COUNT(*) as total FROM sales WHERE created_at::date = now()::date GROUP BY agente ORDER BY total DESC LIMIT 10",
        fetch=True
    )
    
    # Sales by product
    sales_by_product = execute(
        "SELECT producto, COUNT(*) as total FROM sales WHERE created_at::date = now()::date GROUP BY producto ORDER BY total DESC LIMIT 10",
        fetch=True
    )

    # Calculate conversion: Sales / (Sales + NoSales)
    sales = kpi_sales["total"] if kpi_sales else 0
    nosales = kpi_nosale["total"] if kpi_nosale else 0
    total_closed = sales + nosales
    conversion = round((sales / total_closed * 100), 2) if total_closed > 0 else 0

    from datetime import datetime
    return {
        "success": True,
        "agents": agents,
        "stuckLeads": stuck,
        "seguimientos": seguimientos,
        "backofficePending": backoffice,
        "kpis": {
            "queueNew": kpi_queue["total"] if kpi_queue else 0,
            "ventasCantadasHoy": sales,
            "aprobadasPorBOHoy": kpi_approved["total"] if kpi_approved else 0,
            "noVentasHoy": nosales,
            "salesByAgent": {r["agente"]: r["total"] for r in sales_by_agent},
            "salesByProduct": {r["producto"]: r["total"] for r in sales_by_product},
            "conversion": conversion,
            "slaBreached": kpi_sla["total"] if kpi_sla else 0,
            "followupsToday": len(seguimientos)
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
def release_lead(message_id: str):
    """Release a lead back to the queue (coordinator action)."""
    execute(
        """
        UPDATE leads
        SET estado = 'NUEVO', agente = NULL, fecha_asignacion = NULL, 
            liberado_por = 'COORDINADOR', liberado_en = now(), updated_at = now()
        WHERE message_id = %s
        """,
        (message_id,)
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
        "revenuedolar", "suptipo_reco", "tipo_venta_original"
    ]
    for col in columns:
        execute(f"ALTER TABLE sales ADD COLUMN IF NOT EXISTS {col} TEXT")
    
    # Timestamptz columns
    ts_columns = ["vendedor_comentarios_at", "bo_email_enviado_at"]
    for col in ts_columns:
        execute(f"ALTER TABLE sales ADD COLUMN IF NOT EXISTS {col} TIMESTAMPTZ")

    # 2. Cleanup
    for table in ["leads", "sales", "agents"]:
        execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
    return {"success": True, "message": "Database cleaned and schema updated"}
