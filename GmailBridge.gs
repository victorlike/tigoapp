/**
 * GmailBridge.gs — Apps Script (simplified)
 * ONLY reads Gmail and sends leads to the Railway API.
 * No more Sheets writes. Replace RAILWAY_URL and API_KEY below.
 */

// Config now provided by Config.gs

const GMAIL_LABEL = 'TIGO-LEADS';   // Gmail label to scan
const PROCESSED   = 'TIGO-DONE';    // Label to mark processed


function processNewLeads() {
  // Get the unprocessed label
  const label = GmailApp.getUserLabelByName(GMAIL_LABEL);
  if (!label) {
    Logger.log('❌ Label not found: ' + GMAIL_LABEL);
    return;
  }

  const doneLabel = getOrCreateLabel_(PROCESSED);
  const threads = label.getThreads(0, 50);

  let sent = 0;
  threads.forEach(thread => {
    const msg = thread.getMessages()[0];
    if (!msg) return;

    const lead = extractLeadFromEmail_(msg);
    if (!lead) return;

    const ok = postToRailway_(lead);
    if (ok) {
      thread.addLabel(doneLabel);
      thread.removeLabel(label);
      sent++;
    }
  });

  Logger.log('✅ Leads enviados: ' + sent);
}


function extractLeadFromEmail_(msg) {
  const subject = msg.getSubject() || '';
  const body    = msg.getPlainBody() || '';
  const date    = msg.getDate();

  // ─── Parse "Key=Value||" format ────────────────────
  const data = {};
  body.split('||').forEach(part => {
    const pieces = part.split('=');
    if (pieces.length >= 2) {
      const key = pieces[0].trim().toLowerCase();
      const val = pieces.slice(1).join('=').trim();
      data[key] = val;
    }
  });

  // Use Gmail Message-Id as unique identifier
  const messageId = 'gmail_' + Utilities.base64Encode(msg.getId());

  const lead = {
    message_id: messageId,
    nombre:     data.nombre     || null,   // ← No usar el Subject como nombre
    linea:      data.linea      || null,
    plan:       data.plan       || null,
    fecha_gmail: date ? date.toISOString() : new Date().toISOString(),
    tracking:   data.tracking   || null,
    gaid:       data.gaid       || null,
    origen:     data.origen     || null,
    url:        data.url        || null,
    equipo:     data.equipo     || null,
    utm:        data.utm        || null,
    horario:    data.horario    || null,
    timestamp_sheet: data.timestamp || null,
    documento:  data.documento  || null,
    compania:   data.compania   || null,
    operacion:  data.operacion  || null,
    tsource:    data.tsource    || null,
    modal:      data.modal      || null,
    direccion:  data.direccion  || null,
    email:      data.email      || null
  };

  // ─── Fallback Regex Parsing (Si el formato Key=Value no funcionó) ───
  if (!lead.nombre) {
    const n = body.match(/Nombre:\s*([^\n|]+)/i);
    if (n) lead.nombre = n[1].trim();
  }
  if (!lead.linea) {
    const l = body.match(/(?:Línea|Teléfono|Celular|Linea):\s*([\d\s+()\-]+)/i);
    if (l) lead.linea = l[1].replace(/[^\d]/g, '');
  }
  if (!lead.plan) {
    const p = body.match(/Plan:\s*([^\n|]+)/i);
    if (p) lead.plan = p[1].trim();
  }

  // ─── Validación mínima ───────────────────────────────
  if (!lead.linea) {
    Logger.log('⚠️ Lead sin línea detectado. Subject: ' + subject + ' | MessageId: ' + msg.getId());
    // Aún así enviamos — el servidor decide si aceptarlo
  }

  return lead;
}


function postToRailway_(lead) {
  try {
    const baseUrl = RAILWAY_URL.replace(/\/+$/, '');
    const finalUrl = baseUrl + '/api/leads';

    const res = UrlFetchApp.fetch(finalUrl, {
      method: 'POST',
      contentType: 'application/json',
      headers: { 'X-Api-Key': API_KEY },
      payload: JSON.stringify(lead),
      muteHttpExceptions: true
    });

    const code = res.getResponseCode();
    if (code === 200 || code === 201) {
      return true;
    } else {
      const errorText = res.getContentText();
      Logger.log('⚠️ Railway responded ' + code + ': ' + errorText);
      // Optional: Send a notification email to the admin on persistent 403 or 500
      return false;
    }
  } catch (e) {
    Logger.log('❌ Error POST to Railway: ' + e.message);
    return false;
  }
}


function match_(text, regex) {
  const m = text.match(regex);
  return m ? m[1].trim() : null;
}


function getOrCreateLabel_(name) {
  return GmailApp.getUserLabelByName(name) || GmailApp.createLabel(name);
}


/** Run this once to install a trigger every 5 minutes. */
function installTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'processNewLeads') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('processNewLeads')
    .timeBased().everyMinutes(1).create();
  Logger.log('✅ Trigger installed: processNewLeads every 5 min');
}
