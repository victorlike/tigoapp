"""
routes/sales.py — Sales logging
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from models import SaleCreate
import datetime
from database import execute, fetchone
from auth import verify_apps_script_key
from utils.mailer import send_backoffice_email
import logging
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("")
def create_sale(sale: SaleCreate, background_tasks: BackgroundTasks):
    """Register a new sale with full metadata."""
    from utils.logic import normalize_product_group, get_phone_suffix, get_now
    
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

    # 3. Comprehensive Insert (60+ fields)
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
        bo_email_enviado_at, suptipo_reco, created_at, updated_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    created = sale.created_at or get_now()
    updated = sale.updated_at or created
    
    params = (
        sale.message_id, sale.agente, producto, sale.tipo_venta, sale.tipo_venta_original,
        sale.cliente_nombre, sale.cliente_cedula, sale.cliente_email, sale.cliente_telefono,
        sale.dir_depto, sale.dir_ciudad, sale.dir_barrio, sale.dir_calle,
        sale.venta_plan, sale.venta_equipo, sale.venta_pago, sale.vendedor_comentarios,
        sale.tip_tipo, sale.tip_resultado, sale.tip_motivo, sale.tip_submotivo,
        sale.cliente_vendedor, sale.cliente_nacimiento, sale.dir_loc, sale.dir_puerta, sale.dir_tipo,
        sale.dir_apto, sale.dir_esq1, sale.dir_esq2, sale.venta_vigencia, sale.venta_clc,
        sale.venta_llevaequipo, sale.venta_precio, sale.venta_cuotas, sale.dg_solicita, sale.dg_importe,
        sale.dg_corresponde, sale.envio_tipo, sale.envio_detalles, sale.cobro_importe, sale.cobro_motivo,
        sale.cobro_linkemail, sale.link_enviado, sale.nombre_link, sale.plateran_cargado, sale.plateran_so,
        sale.estado_pedido, sale.controldoc_subido, sale.controldoc_estado, sale.porta_nip,
        sale.vendedor_comentarios_por, sale.vendedor_comentarios_at, sale.backoffice_status,
        sale.backoffice_sub_status, sale.backoffice_agent, sale.backoffice_at, sale.backoffice_notas,
        sale.origen, sale.valor_plan, sale.valor_telefono, sale.revenue, sale.revenuedolar,
        sale.bo_email_enviado_at, sale.suptipo_reco, created, updated
    )
    
    execute(query, params)
    
    # Send email to backoffice in background
    background_tasks.add_task(send_backoffice_email, sale)
    
    return {"success": True}


@router.post("/manual")
def create_manual_sale(sale: SaleCreate, background_tasks: BackgroundTasks):
    """
    Creates both a Lead (closed as Venta) and a Sale record for ad-hoc agent entries.
    """
    from utils.logic import normalize_product_group, get_phone_suffix, get_now
    
    # 1. Normalize Product
    producto = normalize_product_group(sale.producto)
    
    # 2. Create the Lead Record (so it exists in the leads table for reporting)
    # Manual sales are inherently "Venta" status
    created = sale.created_at or get_now()
    updated = sale.updated_at or created
    
    execute(
        """
        INSERT INTO leads (
            message_id, nombre, linea, plan, agente, agente_original, 
            estado, resultado, created_at, updated_at, 
            tip_tipo, tip_resultado, tip_motivo, origen, tsource
        ) VALUES (%s, %s, %s, %s, %s, %s, 'Venta', 'Venta', %s, %s, %s, %s, %s, 'manual-referido', 'manual')
        ON CONFLICT (message_id) DO UPDATE SET estado='Venta', updated_at=%s
        """,
        (
            sale.message_id, sale.cliente_nombre, sale.cliente_telefono, sale.venta_plan, 
            sale.agente, sale.agente, created, updated, sale.tip_tipo, sale.tip_resultado, sale.tip_motivo, 
            updated
        )
    )

    # 3. Insert Sale Record (reuse common logic or insert directly)
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
        backoffice_status, created_at, updated_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'Pendiente de carga',%s,%s)
    """
    params = (
        sale.message_id, sale.agente, producto, sale.tipo_venta, sale.tipo_venta_original,
        sale.cliente_nombre, sale.cliente_cedula, sale.cliente_email, sale.cliente_telefono,
        sale.dir_depto, sale.dir_ciudad, sale.dir_barrio, sale.dir_calle,
        sale.venta_plan, sale.venta_equipo, sale.venta_pago, sale.vendedor_comentarios,
        sale.tip_tipo, sale.tip_resultado, sale.tip_motivo, sale.tip_submotivo,
        sale.cliente_vendedor, sale.cliente_nacimiento, sale.dir_loc, sale.dir_puerta, sale.dir_tipo,
        sale.dir_apto, sale.dir_esq1, sale.dir_esq2, sale.venta_vigencia, sale.venta_clc,
        sale.venta_llevaequipo, sale.venta_precio, sale.venta_cuotas, sale.dg_solicita, sale.dg_importe,
        sale.dg_corresponde, sale.envio_tipo, sale.envio_detalles, sale.cobro_importe, sale.cobro_motivo,
        sale.cobro_linkemail, sale.link_enviado, sale.nombre_link, sale.plateran_cargado, sale.plateran_so,
        sale.estado_pedido, sale.controldoc_subido, sale.controldoc_estado, sale.porta_nip,
        created, updated
    )
    
    execute(query, params)
    
    # 4. Trigger Backoffice Email
    background_tasks.add_task(send_backoffice_email, sale)
    
    return {"success": True, "message_id": sale.message_id}


DEFAULT_BO_STATUS_LIST = [
    'Pendiente de carga',
    'Pendiente de firma',
    'Pendiente de pago',
    'Enviada a plateran',
    'Pendiente de retiro en pick up',
    'Pendiente de control de documentación',
    'Documentación rechazada',
    'Venta cancelada falta retoma',
    'Venta cancelada finalizada'
]


@router.get("/backoffice")
def list_backoffice_sales(q: Optional[str] = None):
    """List sales for backoffice processing."""
    query = "SELECT * FROM sales"
    params = []
    if q:
        query += " WHERE cliente_nombre ILIKE %s OR message_id ILIKE %s OR cliente_cedula ILIKE %s"
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    
    query += " ORDER BY created_at DESC LIMIT 200"
    items = execute(query, params, fetch=True)
    return {"success": True, "items": items}


@router.patch("/{message_id}/backoffice")
def update_backoffice_status(message_id: str, status: str, notas: Optional[str] = None, agent: Optional[str] = None):
    """Update the backoffice status and notes for a sale."""
    execute(
        """
        UPDATE sales SET 
            backoffice_status = %s, 
            backoffice_notas = %s, 
            backoffice_agent = %s, 
            backoffice_at = now() 
        WHERE message_id = %s
        """,
        (status, notas, agent, message_id)
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
        bo_email_enviado_at, suptipo_reco, created_at, updated_at
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
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
            s.bo_email_enviado_at, s.suptipo_reco,
            s.created_at or get_now(),
            s.updated_at or s.created_at or get_now()
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
