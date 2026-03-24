"""
routes/seller.py — Agent-specific portal endpoints (Seller Portal)
"""
from fastapi import APIRouter, HTTPException, Depends
from models import SaleCommentUpdate
from database import execute, fetchone
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/sales")
def list_my_sales(email: str):
    """
    List sales belonging to the authenticated agent (legacy parity).
    Deduplicates by MessageId, keeping the most recent.
    """
    sales = execute(
        """
        SELECT DISTINCT ON (message_id) 
            message_id, created_at, producto, cliente_nombre, venta_plan, 
            backoffice_status, vendedor_comentarios, vendedor_comentarios_at
        FROM sales
        WHERE agente = %s
        ORDER BY message_id, created_at DESC
        """,
        (email,),
        fetch=True
    )
    # Sort byproduct of DISTINCT ON by date desc
    sales.sort(key=lambda x: x["created_at"], reverse=True)
    return {"success": True, "items": sales}

@router.patch("/sales/{message_id}/comment")
def update_sale_comment(message_id: str, body: SaleCommentUpdate, email: str):
    """
    Allows agents to add/update vendedor_comentarios for their own sales.
    """
    # Verify ownership
    sale = fetchone("SELECT id FROM sales WHERE message_id = %s AND agente = %s", (message_id, email))
    if not sale:
        raise HTTPException(403, "No tienes permiso para comentar esta venta o no existe.")

    now = datetime.now(timezone.utc)
    execute(
        """
        UPDATE sales
        SET vendedor_comentarios = %s,
            vendedor_comentarios_por = %s,
            vendedor_comentarios_at = %s,
            updated_at = now()
        WHERE message_id = %s
        """,
        (body.comentario, email, now, message_id)
    )
    return {"success": True}

@router.get("/initial_data")
def get_initial_data(email: str):
    """
    Aggregates queue count, my leads, and follow-ups in a single call for the Agent UI.
    Parity with apiGetInitialData().
    """
    # 1. Queue count (New leads today)
    queue = fetchone(
        "SELECT COUNT(*) AS total FROM leads WHERE estado = 'NUEVO' AND agente IS NULL AND created_at >= CURRENT_DATE"
    )
    
    # 2. My Active Leads
    active = execute(
        "SELECT * FROM leads WHERE agente = %s AND estado = 'ASIGNADO' ORDER BY fecha_asignacion ASC",
        (email,),
        fetch=True
    )
    
    # 3. SLA Breaches (Queue > 5 min)
    sla = fetchone(
        "SELECT COUNT(*) AS total FROM leads WHERE estado = 'NUEVO' AND agente IS NULL AND created_at < now() - interval '5 minutes'"
    )

    return {
        "success": True,
        "email": email,
        "queueCount": queue["total"] if queue else 0,
        "myLeads": active,
        "slaBreachedCount": sla["total"] if sla else 0
    }
