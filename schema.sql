-- ============================================================
-- schema.sql — Run this once in Supabase SQL Editor
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── LEADS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id          TEXT UNIQUE NOT NULL,
  nombre              TEXT,
  linea               TEXT,
  plan                TEXT,
  estado              TEXT NOT NULL DEFAULT 'NUEVO',
  agente              TEXT,
  agente_original     TEXT,
  fecha_gmail         TIMESTAMPTZ,
  fecha_asignacion    TIMESTAMPTZ,
  resultado           TEXT,
  rellamar_en         TIMESTAMPTZ,
  reagendar_tipo      TEXT,
  nocontacto_intentos INT NOT NULL DEFAULT 0,
  sla_asignacion      INT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_leads_estado       ON leads(estado);
CREATE INDEX IF NOT EXISTS idx_leads_agente       ON leads(agente);
CREATE INDEX IF NOT EXISTS idx_leads_fecha_gmail  ON leads(fecha_gmail);
CREATE INDEX IF NOT EXISTS idx_leads_message_id   ON leads(message_id);

-- ── AGENTS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agents (
  email         TEXT PRIMARY KEY,
  estado        TEXT NOT NULL DEFAULT 'OFFLINE',
  last_seen     TIMESTAMPTZ,
  max_leads     INT NOT NULL DEFAULT 1,
  last_assigned TIMESTAMPTZ,
  updated_at    TIMESTAMPTZ DEFAULT now()
);

-- ── SALES ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sales (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id          TEXT,
  agente              TEXT,
  fecha               TIMESTAMPTZ DEFAULT now(),
  producto            TEXT,
  tipo_venta          TEXT,
  tipo_venta_original TEXT,
  cliente_nombre      TEXT,
  cliente_cedula      TEXT,
  cliente_email       TEXT,
  cliente_telefono    TEXT,
  dir_depto           TEXT,
  dir_ciudad          TEXT,
  dir_barrio          TEXT,
  dir_calle           TEXT,
  venta_plan          TEXT,
  venta_equipo        TEXT,
  venta_pago          TEXT,
  vendedor_comentarios TEXT,
  backoffice_status   TEXT DEFAULT 'Pendiente de carga',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sales_agente     ON sales(agente);
CREATE INDEX IF NOT EXISTS idx_sales_created_at ON sales(created_at DESC);

-- ── USEFUL VIEWS for BI ────────────────────────────────────
CREATE OR REPLACE VIEW vw_daily_queue AS
SELECT
  DATE_TRUNC('day', fecha_gmail) AS dia,
  COUNT(*) AS total_leads,
  COUNT(*) FILTER (WHERE estado = 'NUEVO' AND agente IS NULL) AS sin_asignar,
  COUNT(*) FILTER (WHERE estado = 'ASIGNADO') AS asignados,
  COUNT(*) FILTER (WHERE estado = 'SEGUIMIENTO') AS seguimiento,
  COUNT(*) FILTER (WHERE resultado = 'VENTA') AS ventas
FROM leads
GROUP BY 1
ORDER BY 1 DESC;
