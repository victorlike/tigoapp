"""
routes/sales.py — Sales logging
"""
from fastapi import APIRouter, Depends, HTTPException
from models import SaleCreate
from database import execute, fetchone
from auth import verify_apps_script_key
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
def create_sale(sale: SaleCreate):
    """Register a new sale."""
    from utils.logic import normalize_product_group, get_phone_suffix
    
    # 1. Normalize Product
    producto = normalize_product_group(sale.producto)
    
    # 2. Duplicate Check (Agent + Phone Suffix + 1 minute)
    suffix = get_phone_suffix(sale.cliente_telefono)
    if suffix:
        existing = fetchone(
            """
            SELECT id FROM sales 
            WHERE agente = %s 
              AND RIGHT(cliente_telefono, 8) = %s 
              AND created_at > now() - interval '1 minute'
            LIMIT 1
            """,
            (sale.agente, suffix)
        )
        if existing:
            return {"success": False, "message": "Duplicado detectado: Ya registraste esta venta hace instantes."}

    execute(
        """
        INSERT INTO sales (
            message_id, agente, producto, tipo_venta, tipo_venta_original,
            cliente_nombre, cliente_cedula, cliente_email, cliente_telefono,
            dir_depto, dir_ciudad, dir_barrio, dir_calle,
            venta_plan, venta_equipo, venta_pago, vendedor_comentarios,
            tip_tipo, tip_resultado, tip_motivo, tip_submotivo,
            created_at
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        """,
        (
            sale.message_id, sale.agente, producto, sale.tipo_venta,
            sale.tipo_venta_original, sale.cliente_nombre, sale.cliente_cedula,
            sale.cliente_email, sale.cliente_telefono,
            sale.dir_depto, sale.dir_ciudad, sale.dir_barrio, sale.dir_calle,
            sale.venta_plan, sale.venta_equipo, sale.venta_pago,
            sale.vendedor_comentarios,
            sale.tip_tipo, sale.tip_resultado, sale.tip_motivo, sale.tip_submotivo
        )
    )
    return {"success": True}


@router.get("/{message_id}")
def get_sale_details(message_id: str):
    """Fetch full details for a single sale (Backoffice modal)."""
    sale = fetchone("SELECT * FROM sales WHERE message_id = %s", (message_id,))
    if not sale:
        raise HTTPException(404, "Venta no encontrada")
    return {"success": True, "sale": sale}


# ─── POST /api/sales/bulk  ─────────────────────────────
@router.post("/bulk", dependencies=[Depends(verify_apps_script_key)])
def bulk_create_sales(sales: list[SaleCreate]):
    """Bulk import sales. Used for migration."""
    if not sales: return {"success": True, "count": 0}
    
    logger.info(f"Bulk importing {len(sales)} sales")
    
    query = """
    INSERT INTO sales (
        message_id, agente, producto, tipo_venta, tipo_venta_original,
        cliente_nombre, cliente_cedula, cliente_email, cliente_telefono,
        dir_depto, dir_ciudad, dir_barrio, dir_calle,
        venta_plan, venta_equipo, venta_pago, vendedor_comentarios,
        tip_tipo, tip_resultado, tip_motivo, tip_submotivo,
        cliente_vendedor, cliente_nacimiento, dir_loc, dir_puerta, dir_tipo,
        dir_apto, dir_esq1, dir_esq2, venta_vigencia, venta_clc,
        venta_llevaequipo, venta_precio, venta_cuotas, dg_solicita, dg_importe,
        dg_corresponde, envio_tipo, envio_detalles, cobro_importe, cobro_motivo,
        cobro_linkemail, link_enviado, nombre_link, plateran_cargado, plateran_so,
        estado_pedido, controldoc_subido, controldoc_estado, porta_nip,
        vendedor_comentarios_por, vendedor_comentarios_at, backoffice_status,
        backoffice_sub_status, backoffice_agent, backoffice_at, backoffice_notas,
        origen, valor_plan, valor_telefono, revenue, revenuedolar,
        bo_email_enviado_at, suptipo_reco, created_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
    """
    params = [
        (
            s.message_id, s.agente, s.producto, s.tipo_venta, s.tipo_venta_original,
            s.cliente_nombre, s.cliente_cedula, s.cliente_email, s.cliente_telefono,
            s.dir_depto, s.dir_ciudad, s.dir_barrio, s.dir_calle,
            s.venta_plan, s.venta_equipo, s.venta_pago, s.vendedor_comentarios,
            s.tip_tipo, s.tip_resultado, s.tip_motivo, s.tip_submotivo,
            s.cliente_vendedor, s.cliente_nacimiento, s.dir_loc, s.dir_puerta, s.dir_tipo,
            s.dir_apto, s.dir_esq1, s.dir_esq2, s.venta_vigencia, s.venta_clc,
            s.venta_llevaequipo, s.venta_precio, s.venta_cuotas, s.dg_solicita, s.dg_importe,
            s.dg_corresponde, s.envio_tipo, s.envio_detalles, s.cobro_importe, s.cobro_motivo,
            s.cobro_linkemail, s.link_enviado, s.nombre_link, s.plateran_cargado, s.plateran_so,
            s.estado_pedido, s.controldoc_subido, s.controldoc_estado, s.porta_nip,
            s.vendedor_comentarios_por, s.vendedor_comentarios_at, s.backoffice_status,
            s.backoffice_sub_status, s.backoffice_agent, s.backoffice_at, s.backoffice_notas,
            s.origen, s.valor_plan, s.valor_telefono, s.revenue, s.revenuedolar,
            s.bo_email_enviado_at, s.suptipo_reco
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
