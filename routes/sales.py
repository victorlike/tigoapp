"""
routes/sales.py — Sales logging
"""
from fastapi import APIRouter, Depends
from models import SaleCreate
from database import execute, fetchone
from auth import verify_apps_script_key

router = APIRouter()


@router.post("")
def create_sale(sale: SaleCreate):
    """Register a new sale."""
    execute(
        """
        INSERT INTO sales (
            message_id, agente, producto, tipo_venta, tipo_venta_original,
            cliente_nombre, cliente_cedula, cliente_email, cliente_telefono,
            dir_depto, dir_ciudad, dir_barrio, dir_calle,
            venta_plan, venta_equipo, venta_pago, vendedor_comentarios
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            sale.message_id, sale.agente, sale.producto, sale.tipo_venta,
            sale.tipo_venta_original, sale.cliente_nombre, sale.cliente_cedula,
            sale.cliente_email, sale.cliente_telefono,
            sale.dir_depto, sale.dir_ciudad, sale.dir_barrio, sale.dir_calle,
            sale.venta_plan, sale.venta_equipo, sale.venta_pago,
            sale.vendedor_comentarios
        )
    )
    return {"success": True}


# ─── POST /api/sales/bulk  ─────────────────────────────
@router.post("/bulk", dependencies=[Depends(verify_apps_script_key)])
def bulk_create_sales(sales: list[SaleCreate]):
    """Bulk import sales. Used for migration."""
    if not sales: return {"success": True, "count": 0}
    
    query = """
    INSERT INTO sales (
        message_id, agente, producto, tipo_venta, tipo_venta_original,
        cliente_nombre, cliente_cedula, cliente_email, cliente_telefono,
        dir_depto, dir_ciudad, dir_barrio, dir_calle,
        venta_plan, venta_equipo, venta_pago, vendedor_comentarios, created_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
    """
    params = [
        (
            s.message_id, s.agente, s.producto, s.tipo_venta,
            s.tipo_venta_original, s.cliente_nombre, s.cliente_cedula,
            s.cliente_email, s.cliente_telefono,
            s.dir_depto, s.dir_ciudad, s.dir_barrio, s.dir_calle,
            s.venta_plan, s.venta_equipo, s.venta_pago,
            s.vendedor_comentarios
        )
        for s in sales
    ]
    
    from database import bulk_execute
    bulk_execute(query, params)
    
    return {"success": True, "count": len(sales)}


@router.get("")
def list_sales(agente: str = None, limit: int = 100):
    """List sales, optionally filtered by agent."""
    if agente:
        rows = execute(
            "SELECT * FROM sales WHERE agente = %s ORDER BY created_at DESC LIMIT %s",
            (agente, limit),
            fetch=True
        )
    else:
        rows = execute(
            "SELECT * FROM sales ORDER BY created_at DESC LIMIT %s",
            (limit,),
            fetch=True
        )
    return {"success": True, "sales": rows}
