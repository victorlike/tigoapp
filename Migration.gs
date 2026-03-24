/**
 * Migration.gs — One-time data migration script
 * Transfers leads, agents, and sales from Google Sheets to Supabase/Railway.
 */

// ─── CONFIGURATION ──────────────────────────────────────
const RAILWAY_URL = 'https://web-production-cbfe.up.railway.app/'; // ← Change this
const API_KEY     = 'gmail2railway2025';    // ← Change this

const BATCH_SIZE  = 100;

function migrateAll() {
  migrateAgents();
  migrateSales();
  migrateLeads();
}

/** 
 * 1. Migrate AGENTS
 */
function migrateAgents() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('agentes');
  if (!sh) return Logger.log('❌ Hoja "agentes" no encontrada');

  const data = sh.getDataRange().getValues();
  const headers = data.shift();
  const map = getHeaderMap_(headers);

  const agents = data.map(row => ({
    email: row[map['Email']],
    estado: row[map['Estado']] || 'OFFLINE',
    last_seen: row[map['LastSeen']] ? new Date(row[map['LastSeen']]).toISOString() : null,
    max_leads: parseInt(row[map['MaxLeads']]) || 1,
    last_assigned: row[map['UltimaActualizacion']] ? new Date(row[map['UltimaActualizacion']]).toISOString() : null
  })).filter(a => a.email);

  postBulk_('/api/agent/bulk', agents);
}

/**
 * 2. Migrate SALES
 */
function migrateSales() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('ventas_detall_backoffice');
  if (!sh) return Logger.log('❌ Hoja "ventas_detall_backoffice" no encontrada');

  const data = sh.getDataRange().getValues();
  const headers = data.shift();
  const map = getHeaderMap_(headers);

  const sales = data.map(row => ({
    message_id: row[map['MessageId']] || row[map['message_id']] || '',
    agente: row[map['Agente']] || '',
    producto: row[map['Producto']] || '',
    tipo_venta: row[map['TipoVenta']] || '',
    cliente_nombre: row[map['Nombre']] || '',
    cliente_cedula: row[map['Cedula']] || '',
    venta_plan: row[map['Plan']] || '',
    venta_equipo: row[map['Equipo']] || ''
  })).filter(s => s.agente);

  // Send in batches
  for (let i = 0; i < sales.length; i += BATCH_SIZE) {
    const chunk = sales.slice(i, i + BATCH_SIZE);
    postBulk_('/api/sales/bulk', chunk);
    Logger.log(`Ventas: ${i + chunk.length} / ${sales.length}`);
  }
}

/**
 * 3. Migrate LEADS (Historical)
 */
function migrateLeads() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('contactos');
  if (!sh) return Logger.log('❌ Hoja "contactos" no encontrada');

  const lastRow = sh.getLastRow();
  // We process in loops to avoid GAS timeout
  let processed = 0;
  
  // You might need to run this function multiple times if you have > 5000 rows
  // Or adjust the loop to start from a specific row
  const startRow = 2; // skip header
  const data = sh.getRange(startRow, 1, lastRow - 1, sh.getLastColumn()).getValues();
  const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  const map = getHeaderMap_(headers);

  const leads = data.map(row => ({
    message_id: row[map['message_id']] || row[map['messageid']] || ('mig_' + row[map['línea']] + '_' + row[map['fecha']]),
    nombre: row[map['nombre']] || '',
    linea: String(row[map['línea']] || row[map['linea']] || ''),
    plan: row[map['plan']] || '',
    estado: row[map['estado']] || 'NUEVO',
    agente: row[map['agente']] || null,
    agente_original: row[map['agenteoriginal']] || row[map['agente']] || null,
    fecha_gmail: row[map['fecha']] ? new Date(row[map['fecha']]).toISOString() : null,
    resultado: row[map['resultado']] || null,
    rellamar_en: row[map['rellamaren']] ? new Date(row[map['rellamaren']]).toISOString() : null,
    // New fields
    tracking: row[map['tracking']] || '',
    gaid: row[map['gaid']] || '',
    tip_tipo: row[map['tip_tipo']] || row[map['tiptipo']] || '',
    tip_resultado: row[map['tip_resultado']] || row[map['tipresultado']] || '',
    tip_motivo: row[map['tip_motivo']] || row[map['tipmotivo']] || '',
    tip_submotivo: row[map['tip_submotivo']] || row[map['tipsubmotivo']] || ''
  })).filter(l => l.message_id);

  for (let i = 0; i < leads.length; i += BATCH_SIZE) {
    const chunk = leads.slice(i, i + BATCH_SIZE);
    postBulk_('/api/leads/bulk', chunk);
    Logger.log(`Leads: ${i + chunk.length} / ${leads.length}`);
  }
}


function postBulk_(path, data) {
  try {
    // Clean up slashes to avoid double //
    const baseUrl = RAILWAY_URL.replace(/\/+$/, '');
    const cleanPath = path.replace(/^\/+/, '');
    const finalUrl = baseUrl + '/' + cleanPath;

    const res = UrlFetchApp.fetch(finalUrl, {
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-Api-Key': API_KEY },
      payload: JSON.stringify(data),
      muteHttpExceptions: true
    });
    
    const responseText = res.getContentText();
    if (res.getResponseCode() !== 200) {
      Logger.log(`❌ Error en ${path}: ${responseText}`);
    }
  } catch (e) {
    Logger.log(`❌ Excepción en ${path}: ${e.message}`);
  }
}

function getHeaderMap_(headers) {
  const map = {};
  headers.forEach((h, i) => {
    // Store both the original and lowercased version for case-insensitive lookups
    const key = h.toString().trim();
    map[key] = i;
    map[key.toLowerCase()] = i;
    map[key.toUpperCase()] = i;
  });
  return map;
}
