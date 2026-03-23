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
    id: str
    message_id: str
    nombre: Optional[str]
    linea: Optional[str]
    plan: Optional[str]
    estado: str
    agente: Optional[str]
    agente_original: Optional[str]
    fecha_gmail: Optional[datetime]
    fecha_asignacion: Optional[datetime]
    resultado: Optional[str]
    rellamar_en: Optional[datetime]
    reagendar_tipo: Optional[str]
    nocontacto_intentos: int
    sla_asignacion: Optional[int]
    created_at: datetime
    updated_at: datetime


# ─── AGENTS ─────────────────────────────────────────────
class AgentStatusUpdate(BaseModel):
    estado: str   # ACTIVO | OFFLINE


class AgentOut(BaseModel):
    email: str
    estado: str
    last_seen: Optional[datetime]
    max_leads: int
    last_assigned: Optional[datetime]
    updated_at: Optional[datetime]


# ─── FOLLOWUPS ──────────────────────────────────────────
class FollowupOut(BaseModel):
    message_id: str
    nombre: Optional[str]
    linea: Optional[str]
    plan: Optional[str]
    rellamar_en: Optional[datetime]
    agente_original: Optional[str]
    reagendar_tipo: Optional[str]
    nocontacto_intentos: int
    due_now: bool


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
