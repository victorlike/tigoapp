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
    linea: Optional[str] = None      # phone number
    plan: Optional[str] = None
    fecha_gmail: Optional[datetime] = None


class LeadStatusUpdate(BaseModel):
    estado: str
    resultado: Optional[str] = None
    rellamar_en: Optional[datetime] = None
    reagendar_tipo: Optional[str] = None
    nocontacto_intentos: Optional[int] = None


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
    nombre: Optional[str]
    linea: Optional[str]
    plan: Optional[str]
    rellamar_en: Optional[datetime]
    agente_original: Optional[str]
    reagendar_tipo: Optional[str]
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


# ─── GENERIC ────────────────────────────────────────────
class ResponseOK(BaseModel):
    success: bool = True
    message: Optional[str] = None
