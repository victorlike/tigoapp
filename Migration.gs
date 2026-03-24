/**
 * Migration.gs — Comprehensive data migration script
 * Transfers leads, agents, and sales from Google Sheets to Supabase/Railway.
 * Handles all columns and multiple lead sheets.
 */

// ─── CONFIGURATION ──────────────────────────────────────
const RAILWAY_URL = 'https://web-production-cbfe.up.railway.app/';
const API_KEY     = 'gmail2railway2025';

const BATCH_SIZE  = 100;

function migrateAll() {
  cleanDatabase();
  migrateAgents();
  migrateSales();
  
  // Migrate Leads from multiple sheets
  const leadSheets = ['contactos', 'leads_seguimiento', 'leads_exitosos', 'leads_descartados'];
  leadSheets.forEach(sheetName => {
    migrateLeadsFromSheet(sheetName);
  });
}

/**
 * 0. Clean Database (truncate all tables)
 */
function cleanDatabase() {
  Logger.log('🧹 Limpiando la base de datos...');
  postBulk_('/api/coordinator/clean', {});
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
  const map = getHeaderMapFromArray_(headers);

  const agents = data.map(row => ({
    email: getValue_(row, map, 'Email'),
    estado: getValue_(row, map, 'Estado') || 'OFFLINE',
    last_seen: parseDate_(getValue_(row, map, 'LastSeen')),
    max_leads: parseInt(getValue_(row, map, 'MaxLeads')) || 1,
    last_assigned: parseDate_(getValue_(row, map, 'UltimaActualizacion'))
  })).filter(a => a.email);

  postBulk_('/api/agent/bulk', agents);
  Logger.log(`Agentes: ${agents.length} migrados.`);
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
  const map = getHeaderMapFromArray_(headers);

  const sales = data.map((row, index) => {
    const agente = getValue_(row, map, 'Agente') || '';
    const messageId = getValue_(row, map, 'MessageId') || getValue_(row, map, 'message_id') || ('sale_' + index + '_' + new Date().getTime());
    
    return {
      message_id: String(messageId),
      agente: agente,
      producto: getValue_(row, map, 'Producto'),
      tipo_venta: getValue_(row, map, 'TipoVenta'),
      tipo_venta_original: getValue_(row, map, 'TipoVentaOriginal'),
      cliente_vendedor: getValue_(row, map, 'Cliente_Vendedor'),
      cliente_nombre: getValue_(row, map, 'Cliente_Nombre'),
      cliente_cedula: getValue_(row, map, 'Cliente_Cedula'),
      cliente_email: getValue_(row, map, 'Cliente_Email'),
      cliente_nacimiento: getValue_(row, map, 'Cliente_Nacimiento'),
      cliente_telefono: getValue_(row, map, 'Cliente_Telefono'),
      dir_depto: getValue_(row, map, 'Dir_Depto'),
      dir_loc: getValue_(row, map, 'Dir_Loc'),
      dir_barrio: getValue_(row, map, 'Dir_Barrio'),
      dir_calle: getValue_(row, map, 'Dir_Calle'),
      dir_puerta: getValue_(row, map, 'Dir_Puerta'),
      dir_tipo: getValue_(row, map, 'Dir_Tipo'),
      dir_apto: getValue_(row, map, 'Dir_Apto'),
      dir_esq1: getValue_(row, map, 'Dir_Esq1'),
      dir_esq2: getValue_(row, map, 'Dir_Esq2'),
      venta_plan: getValue_(row, map, 'Venta_Plan'),
      venta_vigencia: getValue_(row, map, 'Venta_Vigencia'),
      venta_clc: getValue_(row, map, 'Venta_CLC'),
      venta_llevaequipo: getValue_(row, map, 'Venta_LlevaEquipo'),
      venta_equipo: getValue_(row, map, 'Venta_Equipo'),
      venta_pago: getValue_(row, map, 'Venta_Pago'),
      venta_precio: getValue_(row, map, 'Venta_Precio'),
      venta_cuotas: getValue_(row, map, 'Venta_Cuotas'),
      dg_solicita: getValue_(row, map, 'DG_Solicita'),
      dg_importe: getValue_(row, map, 'DG_Importe'),
      dg_corresponde: getValue_(row, map, 'DG_Corresponde'),
      envio_tipo: getValue_(row, map, 'Envio_Tipo'),
      envio_detalles: getValue_(row, map, 'Envio_Detalles'),
      cobro_importe: getValue_(row, map, 'Cobro_Importe'),
      cobro_motivo: getValue_(row, map, 'Cobro_Motivo'),
      cobro_linkemail: getValue_(row, map, 'Cobro_LinkEmail'),
      link_enviado: getValue_(row, map, 'Link_Enviado'),
      nombre_link: getValue_(row, map, 'Nombre_Link'),
      plateran_cargado: getValue_(row, map, 'Plateran_Cargado'),
      plateran_so: getValue_(row, map, 'Plateran_SO'),
      estado_pedido: getValue_(row, map, 'Estado_Pedido'),
      agente_venta: getValue_(row, map, 'AgenteVenta'),
      fecha_asignacion: parseDate_(getValue_(row, map, 'FechaAsignacion')),
      resultado: getValue_(row, map, 'Resultado'),
      fecha_cierre: parseDate_(getValue_(row, map, 'FechaCierre')),
      notas: getValue_(row, map, 'Notas'),
      minutos_asignacion: getValue_(row, map, 'MinutosAsignacion'),
      sla_asignacion: getValue_(row, map, 'SLA_Asignacion'),
      tip_tipo: getValue_(row, map, 'Tip_Tipo'),
      tip_resultado: getValue_(row, map, 'Tip_Resultado'),
      tip_motivo: getValue_(row, map, 'Tip_Motivo'),
      tip_submotivo: getValue_(row, map, 'Tip_Submotivo'),
      rellamar_en: parseDate_(getValue_(row, map, 'RellamarEn')),
      agente_original: getValue_(row, map, 'AgenteOriginal'),
      seguimiento_tomado_por: getValue_(row, map, 'SeguimientoTomadoPor'),
      seguimiento_tomado_en: parseDate_(getValue_(row, map, 'SeguimientoTomadoEn')),
      liberado_por: getValue_(row, map, 'LiberadoPor'),
      liberado_en: parseDate_(getValue_(row, map, 'LiberadoEn')),
      liberado_motivo: getValue_(row, map, 'LiberadoMotivo'),
      reagendar_tipo: getValue_(row, map, 'ReagendarTipo'),
      nocontacto_intentos: getValue_(row, map, 'NoContactoIntentos'),
      controldoc_subido: getValue_(row, map, 'ControlDoc_Subido'),
      controldoc_estado: getValue_(row, map, 'ControlDoc_Estado'),
      porta_nip: getValue_(row, map, 'Porta_NIP'),
      vendedor_comentarios: getValue_(row, map, 'VendedorComentarios'),
      vendedor_comentarios_por: getValue_(row, map, 'VendedorComentariosPor'),
      vendedor_comentarios_at: parseDate_(getValue_(row, map, 'VendedorComentariosAt')),
      backoffice_status: getValue_(row, map, 'BackofficeStatus'),
      backoffice_sub_status: getValue_(row, map, 'BackofficeSubStatus'),
      backoffice_agent: getValue_(row, map, 'BackofficeAgent'),
      backoffice_at: parseDate_(getValue_(row, map, 'BackofficeAt')),
      backoffice_notas: getValue_(row, map, 'BackofficeNotas'),
      origen: getValue_(row, map, 'Origen'),
      valor_plan: getValue_(row, map, 'Valor plan'),
      valor_telefono: getValue_(row, map, 'Valor telefono'),
      revenue: getValue_(row, map, 'Revenue'),
      revenuedolar: getValue_(row, map, 'Revenuedolar'),
      bo_email_enviado_at: parseDate_(getValue_(row, map, 'BO_EmailEnviadoAt')),
      suptipo_reco: getValue_(row, map, 'Suptipo Reco'),
      tip_tipo: getValue_(row, map, 'Tip_Tipo'),
      tip_resultado: getValue_(row, map, 'Tip_Resultado'),
      tip_motivo: getValue_(row, map, 'Tip_Motivo'),
      tip_submotivo: getValue_(row, map, 'Tip_Submotivo')
    };
  }).filter(s => s.agente);

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
function migrateLeadsFromSheet(sheetName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName(sheetName);
  if (!sh) return Logger.log(`⚠️ Hoja "${sheetName}" no encontrada`);

  Logger.log(`🚀 Migrando leads de hoja: ${sheetName}...`);

  const lastRow = sh.getLastRow();
  if (lastRow < 2) return Logger.log(`ℹ️ Hoja "${sheetName}" está vacía.`);

  const data = sh.getRange(2, 1, lastRow - 1, sh.getLastColumn()).getValues();
  const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
  const map = getHeaderMapFromArray_(headers);

  const leads = data.map((row, index) => {
    const messageId = getValue_(row, map, 'MessageId') || getValue_(row, map, 'message_id') || ('mig_' + sheetName + '_' + index + '_' + new Date().getTime());
    const estado = String(getValue_(row, map, 'EstadoLead') || getValue_(row, map, 'Estado') || 'NUEVO').trim().toUpperCase();
    
    return {
      message_id: String(messageId),
      nombre: getValue_(row, map, 'Nombre'),
      linea: getValue_(row, map, 'Linea'),
      plan: getValue_(row, map, 'Plan'),
      estado: estado,
      agente: getValue_(row, map, 'Agente'),
      agente_original: getValue_(row, map, 'AgenteOriginal') || getValue_(row, map, 'Agente'),
      fecha_gmail: parseDate_(getValue_(row, map, 'Fecha Gmail') || getValue_(row, map, 'Fecha')),
      fecha_asignacion: parseDate_(getValue_(row, map, 'FechaAsignacion')),
      resultado: getValue_(row, map, 'Resultado'),
      rellamar_en: parseDate_(getValue_(row, map, 'RellamarEn')),
      reagendar_tipo: getValue_(row, map, 'ReagendarTipo'),
      nocontacto_intentos: parseInt(getValue_(row, map, 'NoContactoIntentos')) || 0,
      sla_asignacion: getValue_(row, map, 'SLA_Asignacion'),
      tip_tipo: getValue_(row, map, 'Tip_Tipo'),
      tip_resultado: getValue_(row, map, 'Tip_Resultado'),
      tip_motivo: getValue_(row, map, 'Tip_Motivo'),
      tip_submotivo: getValue_(row, map, 'Tip_Submotivo'),
      tracking: getValue_(row, map, 'Tracking'),
      gaid: getValue_(row, map, 'GAID'),
      cantidad_ventas: parseInt(getValue_(row, map, 'Cantidad_Ventas')) || 0,
      origen: getValue_(row, map, 'Origen'),
      url: getValue_(row, map, 'Url'),
      equipo: getValue_(row, map, 'Equipo'),
      utm: getValue_(row, map, 'Utm'),
      horario: getValue_(row, map, 'Horario'),
      timestamp_sheet: getValue_(row, map, 'Timestamp'),
      documento: getValue_(row, map, 'Documento'),
      compania: getValue_(row, map, 'Compania'),
      operacion: getValue_(row, map, 'Operacion'),
      tsource: getValue_(row, map, 'Tsource'),
      modal: getValue_(row, map, 'Modal'),
      direccion: getValue_(row, map, 'Direccion'),
      email: getValue_(row, map, 'Email'),
      fecha_cierre: parseDate_(getValue_(row, map, 'FechaCierre')),
      notas: getValue_(row, map, 'Notas'),
      minutos_asignacion: getValue_(row, map, 'MinutosAsignacion'),
      seguimiento_tomado_por: getValue_(row, map, 'SeguimientoTomadoPor'),
      seguimiento_tomado_en: parseDate_(getValue_(row, map, 'SeguimientoTomadoEn')),
      liberado_por: getValue_(row, map, 'LiberadoPor'),
      liberado_en: parseDate_(getValue_(row, map, 'LiberadoEn')),
      liberado_motivo: getValue_(row, map, 'LiberadoMotivo'),
      error: getValue_(row, map, 'Error')
    };
  }).filter(l => l.message_id);

  for (let i = 0; i < leads.length; i += BATCH_SIZE) {
    const chunk = leads.slice(i, i + BATCH_SIZE);
    postBulk_('/api/leads/bulk', chunk);
    Logger.log(`Sheet "${sheetName}": ${i + chunk.length} / ${leads.length}`);
  }
}


function postBulk_(path, data) {
  try {
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

function getHeaderMapFromArray_(headers) {
  const map = {};
  headers.forEach((h, i) => {
    const key = h.toString().trim();
    map[key] = i;
    map[key.toLowerCase()] = i;
    map[key.toUpperCase()] = i;
    // Handle space-to-underscore if sheet headers vary
    map[key.replace(/\s+/g, '_')] = i;
  });
  return map;
}

function getValue_(row, map, key) {
  const idx = map[key] ?? map[key.toLowerCase()] ?? map[key.toUpperCase()] ?? map[key.replace(/\s+/g, '_')];
  if (idx === undefined) return null;
  const val = row[idx];
  if (val === undefined || val === null || val === '') return null;
  return String(val).trim();
}

function parseDate_(val) {
  if (!val) return null;
  try {
    const d = new Date(val);
    if (isNaN(d.getTime())) return null;
    return d.toISOString();
  } catch (e) {
    return null;
  }
}
