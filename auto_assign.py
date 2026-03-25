import logging
from utils.settings import get_setting
from utils.logic import get_now
from database import execute, fetchone, log_audit

logger = logging.getLogger(__name__)

CONNECTED_SECONDS = 90
MAX_LEADS_DEFAULT = 1


def run():
    """
    1. Check if auto-assignment is enabled in settings
    2. Find agents ACTIVO + seen in last 90s + below their max_leads
    3. Find NUEVO leads with no agent
    4. Assign round-robin by (open_leads ASC, last_assigned ASC)
    """
    enabled = get_setting("auto_assign_enabled", "true")
    if enabled != "true":
        logger.info("Auto-assign skipped: disabled in settings")
        return {"assigned": 0, "status": "disabled"}

    log_audit("system", "auto_assign_start", None, "Starting auto-assignment process.")

    now = get_now()

    # Load eligible agents
    agents = execute(
        """
        SELECT a.email, a.max_leads, a.last_assigned,
               COUNT(l.id) FILTER (WHERE l.estado = 'ASIGNADO') AS open_leads
        FROM agents a
        LEFT JOIN leads l ON l.agente = a.email
        WHERE a.estado = 'ACTIVO'
          AND a.last_seen >= (now() - (%s * INTERVAL '1 second'))
        GROUP BY a.email, a.max_leads, a.last_assigned
        HAVING COUNT(l.id) FILTER (WHERE l.estado = 'ASIGNADO') < a.max_leads
        ORDER BY open_leads ASC, a.last_assigned ASC NULLS FIRST
        """,
        (CONNECTED_SECONDS,),
        fetch=True
    )

    if not agents:
        logger.info("Auto-assign: No eligible agents found (ACTIVO + seen in 90s)")
        log_audit("system", "auto_assign_skip", None, "No eligible agents found (ACTIVO + seen in 90s).")
        return {"assigned": 0}

    # Load free leads
    free_leads = execute(
        """
        SELECT id, message_id, fecha_gmail
        FROM leads
        WHERE estado = 'NUEVO' AND agente IS NULL
        ORDER BY fecha_gmail ASC NULLS LAST
        """,
        fetch=True
    )

    if not free_leads:
        logger.info(f"Auto-assign: Found {len(agents)} agents but 0 NUEVO leads")
        log_audit("system", "auto_assign_skip", None, f"Found {len(agents)} eligible agents but 0 NUEVO leads.")
        return {"assigned": 0}

    logger.info(f"Auto-assign: Starting assignment of {len(free_leads)} leads to {len(agents)} agents")

    assigned = 0
    agent_idx = 0

    for lead in free_leads:
        if agent_idx >= len(agents):
            break

        agent = agents[agent_idx]
        execute(
            """
            UPDATE leads
            SET estado = 'ASIGNADO',
                agente = %s,
                agente_original = COALESCE(agente_original, %s),
                fecha_asignacion = %s,
                updated_at = now()
            WHERE id = %s
            """,
            (agent["email"], agent["email"], now, lead["id"])
        )
        execute(
            "UPDATE agents SET last_assigned = %s, updated_at = %s WHERE email = %s",
            (now, now, agent["email"])
        )
        
        log_audit("system", "auto_assign_success", lead["message_id"], f"Assigned to {agent['email']}")

        assigned += 1
        agent["open_leads"] += 1

        if agent["open_leads"] >= agent["max_leads"]:
            agent_idx += 1

    return {"assigned": assigned}
