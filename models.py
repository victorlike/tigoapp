"""
models.py — Pydantic models (request/response validation)
"""
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ─── LEADS ──────────────────────────────────────────────
class LeadCreate(BaseModel):
    """Payload sent by Apps Script when a new email arrives."""
    message_id: str
    nombre: Optional[str] = None
    linea: Optional[str] = None
    plan: Optional[str] = None
    fecha_gmail: Optional[datetime] = None
    tracking: Optional[str] = None
    gaid: Optional[str] = None
    origen: Optional[str] = None
    url: Optional[str] = None
    equipo: Optional[str] = None
    utm: Optional[str] = None
    horario: Optional[str] = None
    timestamp_sheet: Optional[str] = None
    documento: Optional[str] = None
    compania: Optional[str] = None
    operacion: Optional[str] = None
    tsource: Optional[str] = None
    modal: Optional[str] = None
    direccion: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        coerce_numbers_to_str = True


class LeadStatusUpdate(BaseModel):
    estado: str
    resultado: Optional[str] = None
    rellamar_en: Optional[datetime] = None
    reagendar_tipo: Optional[str] = None
    nocontacto_intentos: Optional[int] = None
    # Tipificación
    tip_tipo: Optional[str] = None
    tip_resultado: Optional[str] = None
    tip_motivo: Optional[str] = None
    tip_submotivo: Optional[str] = None
    sale_data: Optional[dict] = None


class LeadRelease(BaseModel):
    """Payload for agent-led lead release."""
    motivo: str


class LeadOut(BaseModel):
    id: Optional[str] = None
    message_id: str
    nombre: Optional[str] = None
    linea: Optional[str] = None
    plan: Optional[str] = None
    estado: str = "NUEVO"
    agente: Optional[str] = None
    agente_original: Optional[str] = None
    fecha_gmail: Optional[datetime] = None
    fecha_asignacion: Optional[datetime] = None
    resultado: Optional[str] = None
    rellamar_en: Optional[datetime] = None
    reagendar_tipo: Optional[str] = None
    nocontacto_intentos: int = 0
    sla_asignacion: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # New fields for alignment
    tip_tipo: Optional[str] = None
    tip_resultado: Optional[str] = None
    tip_motivo: Optional[str] = None
    tip_submotivo: Optional[str] = None
    liberado_por: Optional[str] = None
    liberado_en: Optional[str] = None
    tracking: Optional[str] = None
    gaid: Optional[str] = None
    cantidad_ventas: Optional[str] = None
    
    # Extra fields from multiple sheets
    origen: Optional[str] = None
    url: Optional[str] = None
    equipo: Optional[str] = None
    plan: Optional[str] = None
    utm: Optional[str] = None
    horario: Optional[str] = None
    timestamp_sheet: Optional[str] = None
    documento: Optional[str] = None
    compania: Optional[str] = None
    operacion: Optional[str] = None
    tsource: Optional[str] = None
    modal: Optional[str] = None
    direccion: Optional[str] = None
    email: Optional[str] = None
    fecha_cierre: Optional[str] = None
    notas: Optional[str] = None
    minutos_asignacion: Optional[str] = None
    seguimiento_tomado_por: Optional[str] = None
    seguimiento_tomado_en: Optional[str] = None
    liberado_por: Optional[str] = None
    liberado_en: Optional[str] = None
    liberado_motivo: Optional[str] = None
    error: Optional[str] = None

    class Config:
        coerce_numbers_to_str = True


# ─── AGENTS ─────────────────────────────────────────────
class AgentStatusUpdate(BaseModel):
    estado: str   # ACTIVO | OFFLINE


class AgentOut(BaseModel):
    email: str
    estado: str = "OFFLINE"
    last_seen: Optional[datetime] = None
    role: str = "AGENT"
    max_leads: int = 1
    last_assigned: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ─── FOLLOWUPS ──────────────────────────────────────────
class FollowupOut(BaseModel):
    message_id: str
    nombre: Optional[str] = None
    linea: Optional[str] = None
    plan: Optional[str] = None
    rellamar_en: Optional[datetime] = None
    agente_original: Optional[str] = None
    reagendar_tipo: Optional[str] = None
    nocontacto_intentos: int = 0
    due_now: bool = False


# ─── SALES ──────────────────────────────────────────────
class SaleCreate(BaseModel):
    message_id: str
    agente: str
    producto: str
    tipo_venta: str
    tipo_venta_original: Optional[str] = None
    cliente_nombre: Optional[str] = None
    cliente_cedula: Optional[str] = None
    cliente_email: Optional[str] = None
    cliente_telefono: Optional[str] = None
    dir_depto: Optional[str] = None
    dir_ciudad: Optional[str] = None
    dir_barrio: Optional[str] = None
    dir_calle: Optional[str] = None
    venta_plan: Optional[str] = None
    venta_equipo: Optional[str] = None
    venta_pago: Optional[str] = None
    vendedor_comentarios: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # New fields for alignment
    tip_tipo: Optional[str] = None
    tip_resultado: Optional[str] = None
    tip_motivo: Optional[str] = None
    tip_submotivo: Optional[str] = None

    # New fields for alignment with Sheet "ventas_detall_backoffice"
    cliente_vendedor: Optional[str] = None
    cliente_nacimiento: Optional[str] = None
    dir_loc: Optional[str] = None
    dir_puerta: Optional[str] = None
    dir_tipo: Optional[str] = None
    dir_apto: Optional[str] = None
    dir_esq1: Optional[str] = None
    dir_esq2: Optional[str] = None
    venta_vigencia: Optional[str] = None
    venta_clc: Optional[str] = None
    venta_llevaequipo: Optional[str] = None
    venta_precio: Optional[str] = None
    venta_cuotas: Optional[str] = None
    dg_solicita: Optional[str] = None
    dg_importe: Optional[str] = None
    dg_corresponde: Optional[str] = None
    envio_tipo: Optional[str] = None
    envio_detalles: Optional[str] = None
    cobro_importe: Optional[str] = None
    cobro_motivo: Optional[str] = None
    cobro_linkemail: Optional[str] = None
    link_enviado: Optional[str] = None
    nombre_link: Optional[str] = None
    plateran_cargado: Optional[str] = None
    plateran_so: Optional[str] = None
    estado_pedido: Optional[str] = None
    controldoc_subido: Optional[str] = None
    controldoc_estado: Optional[str] = None
    porta_nip: Optional[str] = None
    vendedor_comentarios_por: Optional[str] = None
    vendedor_comentarios_at: Optional[str] = None
    backoffice_status: Optional[str] = None
    backoffice_sub_status: Optional[str] = None
    backoffice_agent: Optional[str] = None
    backoffice_at: Optional[str] = None
    backoffice_notas: Optional[str] = None
    origen: Optional[str] = None
    valor_plan: Optional[str] = None
    valor_telefono: Optional[str] = None
    revenue: Optional[str] = None
    revenuedolar: Optional[str] = None
    bo_email_enviado_at: Optional[str] = None
    suptipo_reco: Optional[str] = None

    class Config:
        coerce_numbers_to_str = True


# ─── SALES/SELLER ──────────────────────────────────────
class SaleCommentUpdate(BaseModel):
    comentario: str


# ─── CATALOG ──────────────────────────────────────────
class CatalogItem(BaseModel):
    id: int
    item_type: str
    name: str
    price: float
    active: bool

class CatalogItemCreate(BaseModel):
    item_type: str
    name: str
    price: float
    active: bool = True

class CatalogItemUpdate(BaseModel):
    item_type: Optional[str] = None
    name: Optional[str] = None
    price: Optional[float] = None
    active: Optional[bool] = None


# ─── GENERIC ────────────────────────────────────────────
class ResponseOK(BaseModel):
    success: bool = True
    message: Optional[str] = None
