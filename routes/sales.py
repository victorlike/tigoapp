"""
routes/sales.py — Sales logging
"""
from fastapi import APIRouter
from models import SaleCreate
from database import execute, fetchone

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
