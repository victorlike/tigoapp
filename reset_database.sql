-- ============================================================
-- RESET_DATABASE.SQL
-- Run this in Supabase SQL Editor to wipe and recreate everything.
-- ============================================================

-- DANGER: This will delete ALL data.
DROP VIEW IF EXISTS vw_daily_queue;
DROP TABLE IF EXISTS leads CASCADE;
DROP TABLE IF EXISTS sales CASCADE;
DROP TABLE IF EXISTS agents CASCADE;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── LEADS ──────────────────────────────────────────────────
CREATE TABLE leads (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id              TEXT UNIQUE NOT NULL,
  nombre                  TEXT,
  linea                   TEXT,
  plan                    TEXT,
  estado                  TEXT NOT NULL DEFAULT 'NUEVO',
  agente                  TEXT,
  agente_original         TEXT,
  fecha_gmail             TIMESTAMPTZ,
  fecha_asignacion        TIMESTAMPTZ,
  resultado               TEXT,
  rellamar_en             TIMESTAMPTZ,
  reagendar_tipo          TEXT,
  nocontacto_intentos     INT NOT NULL DEFAULT 0,
  sla_asignacion          TEXT,
  
  -- Additional fields from lead sheets
  fecha_cierre            TIMESTAMPTZ,
  notas                   TEXT,
  minutos_asignacion      TEXT,
  seguimiento_tomado_por  TEXT,
  seguimiento_tomado_en   TIMESTAMPTZ,
  liberado_por            TEXT,
  liberado_en             TIMESTAMPTZ,
  liberado_motivo         TEXT,
  error                   TEXT,
  
  tracking                TEXT,
  gaid                    TEXT,
  cantidad_ventas         TEXT,
  
  -- Context metadata
  origen                  TEXT,
  url                     TEXT,
  equipo                  TEXT,
  utm                     TEXT,
  horario                 TEXT,
  timestamp_sheet         TEXT,
  documento               TEXT,
  compania                TEXT,
  operacion               TEXT,
  tsource                 TEXT,
  modal                   TEXT,
  direccion               TEXT,
  email                   TEXT,
  tip_tipo                TEXT,
  tip_resultado           TEXT,
  tip_motivo              TEXT,
  tip_submotivo           TEXT,

  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── AGENTS ─────────────────────────────────────────────────
CREATE TABLE agents (
  email         TEXT PRIMARY KEY,
  estado        TEXT NOT NULL DEFAULT 'OFFLINE',
  last_seen     TIMESTAMPTZ,
  max_leads     INT NOT NULL DEFAULT 1,
  last_assigned TIMESTAMPTZ,
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- ── SALES ──────────────────────────────────────────────────
CREATE TABLE sales (
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id              TEXT,
  agente                  TEXT,
  fecha                   TIMESTAMPTZ DEFAULT now(),
  
  -- Info from Sheet
  cliente_gmail           TEXT,
  origen                  TEXT,
  url                     TEXT,
  equipo                  TEXT,
  utm                     TEXT,
  linea                   TEXT,
  horario                 TEXT,
  timestamp_sheet         TEXT,
  cliente_nombre          TEXT,
  cliente_documento       TEXT,
  compania                TEXT,
  operacion               TEXT,
  tsource                 TEXT,
  modal                   TEXT,
  direccion               TEXT,
  cliente_email           TEXT,
  estado_lead             TEXT,
  agente_venta            TEXT,
  fecha_asignacion        TIMESTAMPTZ,
  resultado               TEXT,
  fecha_cierre            TIMESTAMPTZ,
  notas                   TEXT,
  minutos_asignacion      TEXT,
  sla_asignacion          TEXT,
  tip_tipo                TEXT,
  tip_resultado           TEXT,
  tip_motivo              TEXT,
  tip_submotivo           TEXT,
  rellamar_en             TIMESTAMPTZ,
  agente_original         TEXT,
  seguimiento_tomado_por  TEXT,
  seguimiento_tomado_en   TIMESTAMPTZ,
  liberado_por            TEXT,
  liberado_en             TIMESTAMPTZ,
  liberado_motivo         TEXT,
  reagendar_tipo          TEXT,
  nocontacto_intentos     INT,
  error                   TEXT,
  cantidad_ventas         TEXT,
  tracking                TEXT,
  gaid                    TEXT,
  
  -- Specific Sale fields
  cliente_nacimiento      TEXT,
  producto                TEXT,
  tipo_venta              TEXT,
  cliente_cedula          TEXT,
  cliente_celular         TEXT,
  dir_depto               TEXT,
  dir_ciudad              TEXT,
  dir_barrio              TEXT,
  dir_calle               TEXT,
  dir_puerta              TEXT,
  dir_apto                TEXT,
  venta_plan              TEXT,
  venta_equipo            TEXT,
  venta_pago              TEXT,
  revenue                 TEXT,
  revenuedolar            TEXT,
  vendedor_comentarios    TEXT,
  vendedor_comentarios_por TEXT,
  vendedor_comentarios_at TIMESTAMPTZ,
  
  -- BO fields
  backoffice_status       TEXT DEFAULT 'Pendiente de carga',
  backoffice_sub_status   TEXT,
  backoffice_agent        TEXT,
  backoffice_at           TIMESTAMPTZ,
  backoffice_notas        TEXT,
  bo_email_enviado_at     TIMESTAMPTZ,
  suptipo_reco            TEXT,
  producto                TEXT,
  tipo_venta              TEXT,
  tipo_venta_original     TEXT,

  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── INDICES ────────────────────────────────────────────────
CREATE INDEX idx_leads_estado        ON leads(estado);
CREATE INDEX idx_leads_agente        ON leads(agente);
CREATE INDEX idx_leads_message_id    ON leads(message_id);
CREATE INDEX idx_sales_message_id     ON sales(message_id);
CREATE INDEX idx_sales_agente        ON sales(agente);
CREATE INDEX idx_agents_estado       ON agents(estado);

-- ── VIEWS ──────────────────────────────────────────────────
CREATE OR REPLACE VIEW vw_daily_queue AS
SELECT
  DATE_TRUNC('day', created_at) AS dia,
  COUNT(*) AS total_leads,
  COUNT(*) FILTER (WHERE estado = 'NUEVO' AND agente IS NULL) AS sin_asignar,
  COUNT(*) FILTER (WHERE estado = 'ASIGNADO') AS asignados,
  COUNT(*) FILTER (WHERE estado = 'SEGUIMIENTO') AS seguimiento,
  COUNT(*) FILTER (WHERE resultado = 'VENTA') AS ventas
FROM leads
GROUP BY 1
ORDER BY 1 DESC;
