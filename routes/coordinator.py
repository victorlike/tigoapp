"""
routes/coordinator.py — Coordinator dashboard data
"""
from database import execute, fetchone
from auth import verify_apps_script_key
from fastapi import APIRouter, Depends

router = APIRouter()


@router.get("/dashboard")
def get_dashboard():
    """Return live stats for all coordinator sections."""
    # 1. Queue (NUEVO leads)
    queue = fetchone(
        "SELECT COUNT(*) AS total FROM leads WHERE estado = 'NUEVO' AND agente IS NULL"
    )
    
    # 2. Agents Monitor
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
    
    # 3. Rescue Leads (Stuck > 15 min)
    rescue = execute(
        """
        SELECT message_id, linea, nombre, agente, 
               EXTRACT(EPOCH FROM (now() - updated_at))/60 AS minutes_stuck
        FROM leads
        WHERE estado = 'ASIGNADO' 
          AND updated_at < now() - interval '15 minutes'
        ORDER BY updated_at ASC
        """,
        fetch=True
    )
    
    # 4. Seguimientos (DUE soon or past)
    seguimientos = execute(
        """
        SELECT message_id, nombre, linea, plan, agente_original, rellamar_en, resultado, nocontacto_intentos
        FROM leads
        WHERE estado = 'SEGUIMIENTO'
          AND (rellamar_en < now() + interval '8 hours' OR rellamar_en IS NULL)
        ORDER BY rellamar_en ASC NULLS LAST
        LIMIT 50
        """,
        fetch=True
    )
    
    # 5. Backoffice (Pending validation)
    backoffice = execute(
        """
        SELECT message_id, producto, cliente_nombre, venta_plan, agente, tipo_venta
        FROM sales
        WHERE backoffice_status = 'Pendiente de carga' OR backoffice_status IS NULL
        ORDER BY created_at ASC
        LIMIT 50
        """,
        fetch=True
    )
    
    # 6. KPIs (Today's summary)
    kpis = fetchone(
        """
        SELECT 
            COUNT(*) FILTER (WHERE estado = 'NUEVO') AS queue,
            COUNT(*) FILTER (WHERE resultado = 'Venta' AND fecha_cierre::date = now()::date) AS sales_today,
            COUNT(*) FILTER (WHERE (resultado != 'Venta' OR resultado IS NULL) AND estado = 'CERRADO' AND fecha_cierre::date = now()::date) AS no_sales_today,
            COUNT(*) FILTER (WHERE estado = 'NUEVO' AND created_at < now() - interval '5 minutes') AS sla_breach,
            COUNT(*) FILTER (WHERE estado = 'SEGUIMIENTO' AND (rellamar_en::date = now()::date OR rellamar_en IS NULL)) AS followups_today,
            COUNT(*) FILTER (WHERE backoffice_status = 'Pendiente de carga') AS pending_backoffice
        FROM (
            SELECT estado, resultado, fecha_cierre, created_at, rellamar_en, NULL as backoffice_status FROM leads
            UNION ALL
            SELECT NULL, NULL, NULL, NULL, NULL, backoffice_status FROM sales
        ) combined
        """
    )
    
    return {
        "success": True,
        "queueCount": queue["total"] if queue else 0,
        "agents": agents,
        "rescueLeads": rescue,
        "seguimientos": seguimientos,
        "backoffice": backoffice,
        "kpis": kpis
    }


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
    return {"success": True}


@router.post("/backoffice/approve")
def approve_sale(message_id: str, note: str = ""):
    """Approve a sale in backoffice."""
    execute(
        """
        UPDATE sales
        SET backoffice_status = 'Aprobado', backoffice_notas = %s, backoffice_at = now()
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
        SET estado = 'NUEVO', agente = NULL, fecha_asignacion = NULL, updated_at = now()
        WHERE message_id = %s
        """,
        (message_id,)
    )
    return {"success": True}


@router.post("/clean", dependencies=[Depends(verify_apps_script_key)])
def clean_database():
    """TRUNCATE all main tables for a fresh start. Called by Migration script."""
    # Order matters due to potential (though currently not defined) FKs or just logic
    # schema.sql doesn't have explicit FKs between these, but it's good practice.
    tables = ["leads", "sales", "agents"]
    
    for table in tables:
        execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
    
    return {"success": True, "message": "Database cleaned successfully"}
