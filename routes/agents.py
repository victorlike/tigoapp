"""
routes/agents.py — Agent presence and status management
"""
from fastapi import APIRouter, HTTPException, Depends
from models import AgentStatusUpdate, AgentOut
from database import execute, fetchone
from auth import verify_apps_script_key
from datetime import datetime, timezone
import auto_assign
from typing import Dict, Any

router = APIRouter()

CONNECTED_SECONDS = 90
OPEN_STATE = "ASIGNADO"


# ─── POST /api/agent/touch  ────────────────────────────
@router.post("/touch")
def touch_agent(email: str):
    """Update agent LastSeen (heartbeat). Creates agent if not exists."""
    from utils.settings import get_setting
    from utils.logic import get_now
    email = email.lower().strip()
    
    existing = fetchone("SELECT email FROM agents WHERE email = %s", (email,))
    now = get_now()
    
    if not existing:
        allowed_domain = get_setting("allowed_domain", "@xtendo-it.com").strip().lower()
        if not email.endswith(allowed_domain):
            raise HTTPException(status_code=403, detail=f"Dominio no permitido. Debe terminar en {allowed_domain}")
            
        execute(
            """
            INSERT INTO agents (email, estado, last_seen, max_leads, updated_at)
            VALUES (%s, 'OFFLINE', %s, 1, %s)
            """,
            (email, now, now)
        )
    else:
        execute(
            "UPDATE agents SET last_seen = %s, updated_at = %s WHERE email = %s",
            (now, now, email)
        )
    return {"success": True}


# ─── PATCH /api/agent/status  ──────────────────────────
@router.patch("/status")
def set_agent_status(email: str, body: AgentStatusUpdate):
    """Change agent status: ACTIVO or OFFLINE."""
    if body.estado == "OFFLINE":
        # Block OFFLINE if agent has open leads
        row = fetchone(
            "SELECT COUNT(*) AS n FROM leads WHERE agente = %s AND estado = %s",
            (email, OPEN_STATE)
        )
        if row and row["n"] > 0:
            raise HTTPException(
                409,
                detail=f"No puedes desconectarte con {row['n']} lead(s) abierto(s)."
            )
    from utils.logic import get_now
    now = get_now()
    execute(
        "UPDATE agents SET estado = %s, last_seen = %s, updated_at = %s WHERE email = %s",
        (body.estado, now, now, email)
    )

    # If going ACTIVO, try to assign pending leads
    if body.estado == "ACTIVO":
        auto_assign.run()

    return {"success": True, "estado": body.estado}


# ─── GET /api/agent/init  ──────────────────────────────
@router.get("/init")
def get_agent_init(email: str, login: bool = False):
    """
    Called on page load. Aggregates data needed for the Agent Portal.
    """
    from utils.settings import get_setting
    from utils.logic import get_now
    email = email.lower().strip()
    
    allowed_domain = get_setting("allowed_domain", "@xtendo-it.com").strip().lower()
    if not email.endswith(allowed_domain):
        return {"success": False, "error": f"Dominio de correo no permitido. Debe terminar en {allowed_domain}"}

    now = get_now()
    agent = fetchone("SELECT * FROM agents WHERE email = %s", (email,))
    
    # Update last_seen on every init/refresh
    if agent:
        execute("UPDATE agents SET last_seen = %s, updated_at = %s WHERE email = %s", (now, now, email))
        agent["last_seen"] = now

    # Force OFFLINE if login=True is passed
    if agent and login:
        execute("UPDATE agents SET estado = 'OFFLINE', updated_at = now() WHERE email = %s", (email,))
        agent["estado"] = "OFFLINE"

    if not agent:
        try:
            # Auto-create on first access
            touch_agent(email)
            agent = fetchone("SELECT * FROM agents WHERE email = %s", (email,))
        except HTTPException as e:
            return {"success": False, "error": e.detail}
    
    # Queue count (NUEVO leads)
    q_row = fetchone("SELECT COUNT(*) AS n FROM leads WHERE estado = 'NUEVO'")
    q_count = q_row["n"] if q_row else 0
    
    # SLA breached (NUEVO leads > 15 mins)
    sla_row = fetchone("SELECT COUNT(*) AS n FROM leads WHERE estado = 'NUEVO' AND created_at < now() - interval '15 minutes' AND created_at >= current_date")
    sla_count = sla_row["n"] if sla_row else 0
    
    # My leads (ASIGNADO)
    my_leads = execute(
        "SELECT * FROM leads WHERE agente = %s AND estado = 'ASIGNADO' ORDER BY fecha_asignacion ASC",
        (email,),
        fetch=True
    )
    
    # Roles & Permissions
    is_bo = (agent["role"] in ["COORD", "ADMIN"])
    
    # BO Status list (can be hardcoded or from another table)
    from routes.sales import DEFAULT_BO_STATUS_LIST

    # Catalog
    catalog = execute("SELECT * FROM catalog WHERE active = TRUE ORDER BY item_type, name", fetch=True)
    
    return {
        "success": True,
        "agentEmail": email,
        "agentStatus": agent["estado"],
        "myLeads": my_leads,
        "isBO": is_bo,
        "boAllowed": is_bo,
        "boStatusList": DEFAULT_BO_STATUS_LIST,
        "queueCount": q_count,
        "slaBreachedCount": sla_count,
        "catalog": catalog or []
    }


# ─── GET /api/agent/info  ──────────────────────────────
@router.get("/info", response_model=Dict[str, Any])
def get_agent_info(email: str):
    from utils.settings import get_setting
    email = email.lower().strip()
    
    allowed_domain = get_setting("allowed_domain", "@xtendo-it.com").strip().lower()
    if not email.endswith(allowed_domain):
        return {"success": False, "error": f"Dominio de correo no permitido. Por favor usa un correo que termine en {allowed_domain}"}
    
    # Check if agent exists
    agent = fetchone("SELECT * FROM agents WHERE email = %s", (email,))
    
    # If not exists, auto-create
    if not agent:
        from utils.logic import get_now
        now = get_now()
        execute(
            "INSERT INTO agents (email, estado, last_seen, max_leads, updated_at, role) VALUES (%s, %s, %s, %s, %s, %s)",
            (email, 'OFFLINE', now, 1, now, 'AGENT')
        )
        agent = fetchone("SELECT * FROM agents WHERE email = %s", (email,))
        
    return {"success": True, "agent": agent}


# ─── POST /api/agent/bulk  ─────────────────────────────
@router.post("/bulk", dependencies=[Depends(verify_apps_script_key)])
def bulk_create_agents(agents: list[AgentOut]):
    """Bulk import agents. Used for migration."""
    if not agents: return {"success": True, "count": 0}
    
    query = """
    INSERT INTO agents (email, estado, last_seen, max_leads, last_assigned, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (email) DO UPDATE SET
        estado = EXCLUDED.estado,
        last_seen = EXCLUDED.last_seen,
        max_leads = EXCLUDED.max_leads,
        last_assigned = EXCLUDED.last_assigned,
        updated_at = EXCLUDED.updated_at
    """
    from utils.logic import get_now
    params = [
        (a.email, a.estado, a.last_seen, a.max_leads, a.last_assigned, a.updated_at or get_now())
        for a in agents
    ]
    
    from database import bulk_execute
    bulk_execute(query, params)
    
    return {"success": True, "count": len(agents)}


# ─── GET /api/agent/list (coordinator) ─────────────────
@router.get("/list")
def list_agents():
    """List all agents with their current open lead count."""
    rows = execute(
        """
        SELECT a.*,
               COUNT(l.id) FILTER (WHERE l.estado = 'ASIGNADO') AS open_leads
        FROM agents a
        LEFT JOIN leads l ON l.agente = a.email
        GROUP BY a.email
        ORDER BY a.email
        """,
        fetch=True
    )
    return {"success": True, "agents": rows}
# ─── POST /api/agent/take  ─────────────────────────────
@router.post("/take")
def take_lead(email: str):
    """Manually pull a lead from the queue."""
    agent = fetchone(
        """
        SELECT a.email, a.max_leads,
               COUNT(l.id) FILTER (WHERE l.estado = 'ASIGNADO') AS open_leads
        FROM agents a
        LEFT JOIN leads l ON l.agente = a.email
        WHERE a.email = %s
        GROUP BY a.email, a.max_leads
        """,
        (email,)
    )
    if not agent:
        raise HTTPException(404, "Agent not found")
    
    if agent["open_leads"] >= agent["max_leads"]:
        return {"success": False, "message": "Maximum leads reached"}

    # Find the oldest unassigned lead
    lead = fetchone(
        "SELECT id, message_id, linea FROM leads WHERE estado = 'NUEVO' AND agente IS NULL ORDER BY fecha_gmail ASC LIMIT 1"
    )
    if not lead:
        return {"success": False, "message": "No leads in queue"}

    from utils.logic import get_now
    now = get_now()
    execute(
        """
        UPDATE leads
        SET estado = 'ASIGNADO', agente = %s, agente_original = COALESCE(agente_original, %s),
            fecha_asignacion = %s, updated_at = now()
        WHERE id = %s
        """,
        (email, email, now, lead["id"])
    )
    execute(
        "UPDATE agents SET last_assigned = %s, updated_at = %s WHERE email = %s",
        (now, now, email)
    )

    return {"success": True, "lead": lead}


# ─── POST /api/agent/manual_sale  ──────────────────────
@router.post("/manual_sale")
def create_manual_sale(email: str, linea: str, nombre: str = ""):
    """Create a lead directly in ASIGNADO state for manual sale."""
    from utils.logic import get_now
    now = get_now()
    message_id = f"manual-{int(now.timestamp() * 1000)}"
    
    execute(
        """
        INSERT INTO leads (message_id, nombre, linea, estado, agente, agente_original, fecha_asignacion, created_at, updated_at)
        VALUES (%s, %s, %s, 'ASIGNADO', %s, %s, %s, %s, %s)
        """,
        (message_id, nombre, linea, email, email, now, now, now)
    )
    
    return {"success": True, "message_id": message_id}
