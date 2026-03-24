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
    sla_asignacion: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    # New fields for alignment
    tip_tipo: Optional[str] = None
    tip_resultado: Optional[str] = None
    tip_motivo: Optional[str] = None
    tip_submotivo: Optional[str] = None
    liberado_por: Optional[str] = None
    liberado_en: Optional[datetime] = None
    liberado_motivo: Optional[str] = None
    tracking: Optional[str] = None
    gaid: Optional[str] = None
    cantidad_ventas: int = 0


# ─── AGENTS ─────────────────────────────────────────────
class AgentStatusUpdate(BaseModel):
    estado: str   # ACTIVO | OFFLINE


class AgentOut(BaseModel):
    email: str
    estado: str = "OFFLINE"
    last_seen: Optional[datetime] = None
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
    
    # New fields for alignment
    tip_tipo: Optional[str] = None
    tip_resultado: Optional[str] = None
    tip_motivo: Optional[str] = None
    tip_submotivo: Optional[str] = None


# ─── GENERIC ────────────────────────────────────────────
class ResponseOK(BaseModel):
    success: bool = True
    message: Optional[str] = None
