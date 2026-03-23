"""
auto_assign.py — Assign unassigned leads to available agents
Runs after a new lead arrives or an agent goes ACTIVO.
"""
from database import execute, fetchone
from datetime import datetime, timezone

CONNECTED_SECONDS = 90
MAX_LEADS_DEFAULT = 1


def run():
    """
    1. Find agents ACTIVO + seen in last 90s + below their max_leads
    2. Find NUEVO leads with no agent
    3. Assign round-robin by (open_leads ASC, last_assigned ASC)
    """
    now = datetime.now(timezone.utc)

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
        return {"assigned": 0}

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

        assigned += 1
        agent["open_leads"] += 1

        if agent["open_leads"] >= agent["max_leads"]:
            agent_idx += 1

    return {"assigned": assigned}
