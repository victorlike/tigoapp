-- ============================================================
-- schema.sql — Full updated schema for Tigo Leads
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── LEADS ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS leads (
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
  id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  message_id              TEXT,
  agente                  TEXT,
  fecha                   TIMESTAMPTZ DEFAULT now(),
  
  cliente_gmail           TEXT,
  linea                   TEXT,
  horario                 TEXT,
  timestamp_sheet         TEXT,
  cliente_vendedor        TEXT,
  cliente_nombre          TEXT,
  cliente_cedula          TEXT,
  cliente_email           TEXT,
  cliente_nacimiento      TEXT,
  cliente_telefono        TEXT,
  dir_depto               TEXT,
  dir_loc                 TEXT,
  dir_ciudad              TEXT,
  dir_barrio              TEXT,
  dir_calle               TEXT,
  dir_puerta              TEXT,
  dir_tipo                TEXT,
  dir_apto                TEXT,
  dir_esq1                TEXT,
  dir_esq2                TEXT,
  venta_plan              TEXT,
  venta_vigencia          TEXT,
  venta_clc               TEXT,
  venta_llevaequipo       TEXT,
  venta_equipo            TEXT,
  venta_pago              TEXT,
  venta_precio            TEXT,
  venta_cuotas            TEXT,
  dg_solicita             TEXT,
  dg_importe              TEXT,
  dg_corresponde          TEXT,
  envio_tipo              TEXT,
  envio_detalles          TEXT,
  cobro_importe           TEXT,
  cobro_motivo            TEXT,
  cobro_linkemail         TEXT,
  link_enviado            TEXT,
  nombre_link             TEXT,
  plateran_cargado        TEXT,
  plateran_so             TEXT,
  estado_pedido           TEXT,
  controldoc_subido       TEXT,
  controldoc_estado       TEXT,
  porta_nip               TEXT,
  vendedor_comentarios    TEXT,
  vendedor_comentarios_por TEXT,
  vendedor_comentarios_at TIMESTAMPTZ,
  backoffice_status       TEXT DEFAULT 'Pendiente de carga',
  backoffice_sub_status   TEXT,
  backoffice_agent        TEXT,
  backoffice_at           TIMESTAMPTZ,
  backoffice_notas        TEXT,
  origen                  TEXT,
  url                     TEXT,
  equipo                  TEXT,
  utm                     TEXT,
  valor_plan              TEXT,
  valor_telefono          TEXT,
  revenue                 TEXT,
  revenuedolar            TEXT,
  bo_email_enviado_at     TIMESTAMPTZ,
  suptipo_reco            TEXT,
  producto                TEXT,
  tipo_venta              TEXT,
  tipo_venta_original     TEXT,

  created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── AUDIT LOGS ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
  id          SERIAL PRIMARY KEY,
  timestamp   TIMESTAMPTZ DEFAULT now(),
  actor       TEXT NOT NULL,
  action      TEXT NOT NULL,
  target      TEXT,
  details     TEXT
);

-- ── CATALOG ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS catalog (
  id          SERIAL PRIMARY KEY,
  item_type   TEXT NOT NULL,
  name        TEXT NOT NULL,
  price       NUMERIC(10,2),
  active      BOOLEAN DEFAULT TRUE,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- ── SETTINGS ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
  key         TEXT PRIMARY KEY,
  value       TEXT NOT NULL,
  updated_at  TIMESTAMPTZ DEFAULT now()
);

-- Default settings (safe to re-run)
INSERT INTO settings (key, value) VALUES
  ('auto_assign_enabled', 'true'),
  ('sla_min', '5'),
  ('stuck_min', '15'),
  ('allowed_domain', '@xtendo-it.com')
ON CONFLICT (key) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_leads_estado        ON leads(estado);
CREATE INDEX IF NOT EXISTS idx_leads_agente        ON leads(agente);
CREATE INDEX IF NOT EXISTS idx_sales_message_id     ON sales(message_id);

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
