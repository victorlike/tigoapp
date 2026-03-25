/**
 * Migration.gs — Comprehensive data migration script
 * Transfers leads, agents, and sales from Google Sheets to Supabase/Railway.
 * Handles all columns and multiple lead sheets.
 */

// ─── CONFIGURATION ──────────────────────────────────────
// Config now provided by Config.gs

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

  // Finally, apply liberations
  migrateLeadsLiberados();
}

/**
 * 4. Apply Liberations (Updates existing leads)
 */
function migrateLeadsLiberados() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName('leads_liberados');
  if (!sh) return Logger.log('ℹ️ Hoja "leads_liberados" no encontrada');

  const data = sh.getDataRange().getValues();
  const headers = data.shift();
  const map = getHeaderMapFromArray_(headers);

  const updates = data.map(row => ({
    message_id: getValue_(row, map, 'MessageId', 1),
    liberado_por: getValue_(row, map, 'LiberadoPor', 3),
    liberado_en: parseDate_(getValue_(row, map, 'Fecha', 0)),
    liberado_motivo: getValue_(row, map, 'Motivo', 4)
  })).filter(u => u.message_id);

  // We need a specific endpoint for updating liberations, or reuse bulk_leads
  // For now, we'll send them to a dedicated update endpoint or leads/bulk 
  // (if leads/bulk supports partial updates, which standard UPSERT does)
  postBulk_('/api/leads/bulk', updates);
  Logger.log(`Liberaciones: ${updates.length} procesadas.`);
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
    const agente = getValue_(row, map, 'Agente', 1) || '';
    const messageId = getValue_(row, map, 'MessageId', 2) || getValue_(row, map, 'message_id', 2) || ('sale_' + index + '_' + new Date().getTime());
    
    return {
      message_id: String(messageId),
      agente: agente,
      producto: getValue_(row, map, 'Producto', 3),
      tipo_venta: getValue_(row, map, 'TipoVenta', 5),
      tipo_venta_original: getValue_(row, map, 'TipoVentaOriginal', 4),
      cliente_vendedor: getValue_(row, map, 'Cliente_Vendedor', 6),
      cliente_nombre: getValue_(row, map, 'Cliente_Nombre', 7),
      cliente_cedula: getValue_(row, map, 'Cliente_Cedula', 8),
      cliente_email: getValue_(row, map, 'Cliente_Email', 9),
      cliente_nacimiento: getValue_(row, map, 'Cliente_Nacimiento', 10),
      cliente_telefono: getValue_(row, map, 'Cliente_Telefono', 11),
      dir_depto: getValue_(row, map, 'Dir_Depto', 12),
      dir_loc: getValue_(row, map, 'Dir_Loc', 13),
      dir_barrio: getValue_(row, map, 'Dir_Barrio', 14),
      dir_calle: getValue_(row, map, 'Dir_Calle', 15),
      dir_puerta: getValue_(row, map, 'Dir_Puerta', 16),
      dir_tipo: getValue_(row, map, 'Dir_Tipo', 17),
      dir_apto: getValue_(row, map, 'Dir_Apto', 18),
      dir_esq1: getValue_(row, map, 'Dir_Esq1', 19),
      dir_esq2: getValue_(row, map, 'Dir_Esq2', 20),
      venta_plan: getValue_(row, map, 'Venta_Plan', 21),
      venta_vigencia: getValue_(row, map, 'Venta_Vigencia', 22),
      venta_clc: getValue_(row, map, 'Venta_CLC', 23),
      venta_llevaequipo: getValue_(row, map, 'Venta_LlevaEquipo', 24),
      venta_equipo: getValue_(row, map, 'Venta_Equipo', 25),
      venta_pago: getValue_(row, map, 'Venta_Pago', 26),
      venta_precio: getValue_(row, map, 'Venta_Precio', 27),
      venta_cuotas: getValue_(row, map, 'Venta_Cuotas', 28),
      dg_solicita: getValue_(row, map, 'DG_Solicita', 29),
      dg_importe: getValue_(row, map, 'DG_Importe', 30),
      dg_corresponde: getValue_(row, map, 'DG_Corresponde', 31),
      envio_tipo: getValue_(row, map, 'Envio_Tipo', 32),
      envio_detalles: getValue_(row, map, 'Envio_Detalles', 33),
      cobro_importe: getValue_(row, map, 'Cobro_Importe', 34),
      cobro_motivo: getValue_(row, map, 'Cobro_Motivo', 35),
      cobro_linkemail: getValue_(row, map, 'Cobro_LinkEmail', 36),
      link_enviado: getValue_(row, map, 'Link_Enviado', 37),
      nombre_link: getValue_(row, map, 'Nombre_Link', 38),
      plateran_cargado: getValue_(row, map, 'Plateran_Cargado', 39),
      plateran_so: getValue_(row, map, 'Plateran_SO', 40),
      estado_pedido: getValue_(row, map, 'Estado_Pedido', 41),
      agente_venta: getValue_(row, map, 'AgenteVenta', 1),
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
      controldoc_subido: getValue_(row, map, 'ControlDoc_Subido', 42),
      controldoc_estado: getValue_(row, map, 'ControlDoc_Estado', 43),
      porta_nip: getValue_(row, map, 'Porta_NIP', 44),
      vendedor_comentarios: getValue_(row, map, 'VendedorComentarios', 45),
      vendedor_comentarios_por: getValue_(row, map, 'VendedorComentariosPor', 46),
      vendedor_comentarios_at: parseDate_(getValue_(row, map, 'VendedorComentariosAt', 47)),
      backoffice_status: getValue_(row, map, 'BackofficeStatus', 48),
      backoffice_sub_status: getValue_(row, map, 'BackofficeSubStatus', 49),
      backoffice_agent: getValue_(row, map, 'BackofficeAgent', 50),
      backoffice_at: parseDate_(getValue_(row, map, 'BackofficeAt', 51)),
      backoffice_notas: getValue_(row, map, 'BackofficeNotas', 53),
      origen: getValue_(row, map, 'Origen', 52),
      valor_plan: getValue_(row, map, 'Valor plan', 54),
      valor_telefono: getValue_(row, map, 'Valor telefono', 55),
      revenue: getValue_(row, map, 'Revenue', 56),
      revenuedolar: getValue_(row, map, 'Revenuedolar', 57),
      bo_email_enviado_at: parseDate_(getValue_(row, map, 'BO_EmailEnviadoAt', 58)),
      suptipo_reco: getValue_(row, map, 'Suptipo Reco', 59),
      tip_tipo: getValue_(row, map, 'Tip_Tipo'),
      tip_resultado: getValue_(row, map, 'Tip_Resultado'),
      venta_equipo: getValue_(headers, row, ["Venta Reco", "Equipo"]),
      vendedor_comentarios: getValue_(headers, row, ["COMENTARIOS", "OBSERVACIONES"]),
      
      // -- Backoffice Expansion Fields --
      backoffice_status: getValue_(headers, row, ["Estado"]),
      backoffice_sub_status: getValue_(headers, row, ["SubEstado"]),
      bo_fecha_preventa: parseDate_(getValue_(headers, row, ["Fecha de Preventa", "fecha pre"])),
      bo_fecha_proceso: parseDate_(getValue_(headers, row, ["fecha de proceso", "fecha pro"])),
      bo_procesado_cancelado: getValue_(headers, row, ["Procesado cancelado"]),
      bo_fecha_cancelado: parseDate_(getValue_(headers, row, ["Fecha de procesado cancelado"])),
      bo_subtipo_venta: getValue_(headers, row, ["Subtipo de venta"]),
      suptipo_reco: getValue_(headers, row, ["Suptipo Reco"]),
      bo_columna1: getValue_(headers, row, ["Columna1"]),
      backoffice_agent: getValue_(headers, row, ["BO"]),
      bo_fecha_generic: parseDate_(getValue_(headers, row, ["FECHA"])),
      bo_seguimiento: getValue_(headers, row, ["SEGUIMIENTO"]),
      bo_seguimiento_interaccion: getValue_(headers, row, ["seguimiento interaccion"]),

      created_at: parseDate_(getValue_(headers, row, ["Fecha", "FECHA CUADRO"])) || new Date(),
      updated_at: parseDate_(getValue_(row, map, 'FechaCierre', 117) || getValue_(row, map, 'Fecha', 0) || new Date())
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
    // ─── Estado Mapping Logic ──────────────────────
    let estado = String(getValue_(row, map, 'EstadoLead') || getValue_(row, map, 'Estado') || '').trim().toUpperCase();
    let resultado = getValue_(row, map, 'Resultado');

    if (!estado) {
      if (sheetName === 'leads_seguimiento') estado = 'SEGUIMIENTO';
      else if (sheetName === 'leads_exitosos' || sheetName === 'leads_descartados') estado = 'CERRADO';
      else estado = 'NUEVO';
    }

    // Force result if missing for dead sheets
    if (!resultado) {
      if (sheetName === 'leads_exitosos') resultado = 'VENTA';
      if (sheetName === 'leads_descartados') resultado = 'No Venta';
    }

    return {
      message_id: getValue_(row, map, 'MessageId', 17) || getValue_(row, map, 'message_id', 17) || ('mig_' + sheetName + '_' + index + '_' + new Date().getTime()),
      nombre: getValue_(row, map, 'Nombre') || getValue_(row, map, 'nombre'), // Name seems missing in CSV
      linea: getValue_(row, map, 'Linea', 6) || getValue_(row, map, 'linea', 6),
      plan: getValue_(row, map, 'Plan', 4) || getValue_(row, map, 'plan', 4),
      estado: estado,
      agente: getValue_(row, map, 'Agente', 19) || getValue_(row, map, 'agente', 19),
      agente_original: getValue_(row, map, 'AgenteOriginal') || getValue_(row, map, 'Agente', 19),
      fecha_gmail: parseDate_(getValue_(row, map, 'Fecha Gmail', 0) || getValue_(row, map, 'Fecha', 0)),
      fecha_asignacion: parseDate_(getValue_(row, map, 'FechaAsignacion', 20)),
      resultado: resultado,
      rellamar_en: parseDate_(getValue_(row, map, 'RellamarEn')),
      reagendar_tipo: getValue_(row, map, 'ReagendarTipo', 23),
      nocontacto_intentos: parseInt(getValue_(row, map, 'NoContactoIntentos')) || 0,
      sla_asignacion: getValue_(row, map, 'SLA_Asignacion'),
      tip_tipo: getValue_(row, map, 'Tip_Tipo'),
      tip_resultado: getValue_(row, map, 'Tip_Resultado'),
      tip_motivo: getValue_(row, map, 'Tip_Motivo'),
      tip_submotivo: getValue_(row, map, 'Tip_Submotivo'),
      tracking: getValue_(row, map, 'Tracking', 5),
      gaid: getValue_(row, map, 'GAID'),
      cantidad_ventas: parseInt(getValue_(row, map, 'Cantidad_Ventas')) || 0,
      origen: getValue_(row, map, 'Origen', 1),
      url: getValue_(row, map, 'Url', 2),
      equipo: getValue_(row, map, 'Equipo', 3),
      utm: getValue_(row, map, 'Utm', 5),
      horario: getValue_(row, map, 'Horario', 7),
      timestamp_sheet: getValue_(row, map, 'Timestamp', 8),
      documento: getValue_(row, map, 'Documento'),
      compania: getValue_(row, map, 'Compania'),
      operacion: getValue_(row, map, 'Operacion', 12),
      tsource: getValue_(row, map, 'Tsource'),
      modal: getValue_(row, map, 'Modal'),
      direccion: getValue_(row, map, 'Direccion'),
      email: getValue_(row, map, 'Email', 16),
      fecha_cierre: parseDate_(getValue_(row, map, 'FechaCierre', 22)),
      notas: getValue_(row, map, 'Notas', 23),
      minutos_asignacion: getValue_(row, map, 'MinutosAsignacion'),
      seguimiento_tomado_por: getValue_(row, map, 'SeguimientoTomadoPor'),
      seguimiento_tomado_en: parseDate_(getValue_(row, map, 'SeguimientoTomadoEn')),
      liberado_por: getValue_(row, map, 'LiberadoPor'),
      liberado_en: parseDate_(getValue_(row, map, 'LiberadoEn')),
      liberado_motivo: getValue_(row, map, 'LiberadoMotivo'),
      error: getValue_(row, map, 'Error'),
      created_at: parseDate_(getValue_(row, map, 'Fecha Gmail', 0) || getValue_(row, map, 'Fecha', 0) || new Date()),
      updated_at: parseDate_(getValue_(row, map, 'FechaCierre', 22) || getValue_(row, map, 'Fecha Gmail', 0) || new Date())
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

function getValue_(row, map, key, indexFallback = null) {
  const idx = map[key] ?? map[key.toLowerCase()] ?? map[key.toUpperCase()] ?? map[key.replace(/\s+/g, '_')];
  
  // Use index fallback if header not found
  const finalIdx = (idx !== undefined) ? idx : indexFallback;
  
  if (finalIdx === null || finalIdx === undefined) return null;
  const val = row[finalIdx];
  if (val === undefined || val === null || val === '') return null;
  return String(val).trim();
}

function parseDate_(val) {
  if (!val) return null;
  if (val instanceof Date) return val.toISOString();
  
  const s = String(val).trim();
  if (!s) return null;

  try {
    // Try native first
    let d = new Date(s);
    if (!isNaN(d.getTime())) return d.toISOString();

    // Fallback for DD/MM/YYYY HH:mm:ss
    const parts = s.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(.*)$/);
    if (parts) {
      const day = parseInt(parts[1], 10);
      const month = parseInt(parts[2], 10) - 1;
      const year = parseInt(parts[3], 10);
      const timePart = parts[4].trim();
      
      let d2 = new Date(year, month, day);
      if (timePart) {
        const timeParts = timePart.match(/(\d{1,2}):(\d{1,2}):?(\d{1,2})?/);
        if (timeParts) {
          d2.setHours(parseInt(timeParts[1], 10) || 0);
          d2.setMinutes(parseInt(timeParts[2], 10) || 0);
          d2.setSeconds(parseInt(timeParts[3], 10) || 0);
        }
      }
      return d2.toISOString();
    }
    return null;
  } catch (e) {
    return null;
  }
}
