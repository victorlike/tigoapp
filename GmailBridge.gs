/**
 * GmailBridge.gs — Apps Script (simplified)
 * ONLY reads Gmail and sends leads to the Railway API.
 * No more Sheets writes. Replace RAILWAY_URL and API_KEY below.
 */

const RAILWAY_URL = 'https://YOUR_APP.railway.app';  // ← change this
const API_KEY     = 'your-apps-script-api-key';       // ← must match APPS_SCRIPT_KEY in Railway env

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

  // ─── Parse fields from email body ────────────────────
  // Adjust these regexes to match your actual email format
  const nombre  = match_(body, /(?:Nombre|Name)[:\s]+(.+)/i);
  const linea   = match_(body, /(?:Teléfono|Línea|Phone)[:\s]+([+\d\s\-]+)/i);
  const plan    = match_(body, /(?:Plan)[:\s]+(.+)/i);

  // Use Gmail Message-Id as unique identifier
  const messageId = 'gmail_' + Utilities.base64Encode(msg.getId());

  return {
    message_id: messageId,
    nombre: nombre || subject,
    linea: linea || null,
    plan: plan || null,
    fecha_gmail: date ? date.toISOString() : new Date().toISOString()
  };
}


function postToRailway_(lead) {
  try {
    const res = UrlFetchApp.fetch(RAILWAY_URL + '/api/leads', {
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
      Logger.log('⚠️ Railway responded ' + code + ': ' + res.getContentText());
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
    .timeBased().everyMinutes(5).create();
  Logger.log('✅ Trigger installed: processNewLeads every 5 min');
}
