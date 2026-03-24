import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from models import SaleCreate

logger = logging.getLogger(__name__)

# Configuración desde variables de entorno
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
RECIPIENTS = [
    'cinthia.serrano@xtendo-it.com',
    'mayra.calizaya@xtendo-it.com',
    'gilberto.vasquez@xtendo-it.com'
]
FILTERED_RECIPIENTS = [
    {'email': 'stephany.aguilera@xtendo-it.com', 'filter': 'PORTA'}
]

def send_backoffice_email(sale: SaleCreate):
    """
    Replicates the Apps Script BACKOFFICE EMAILER logic.
    Sends an HTML email with sale details.
    """
    if not SMTP_USER or not SMTP_PASS:
        logger.warning("SMTP credentials not set. Skipping backoffice email.")
        return False

    try:
        # 1. Determine recipients
        msg_recipients = list(RECIPIENTS)
        tipo = (sale.tipo_venta or "").upper()
        tipo_orig = (sale.tipo_venta_original or "").upper()
        
        for cfg in FILTERED_RECIPIENTS:
            f = cfg['filter'].upper()
            if f in tipo or f in tipo_orig:
                if cfg['email'] not in msg_recipients:
                    msg_recipients.append(cfg['email'])

        # 2. Build HTML Body
        html = build_sale_html(sale)
        
        # 3. Create Message
        msg = MIMEMultipart()
        msg['From'] = f"Tigo Leads Bot <{SMTP_USER}>"
        msg['To'] = ", ".join(msg_recipients)
        msg['Subject'] = f"Backoffice | Venta Nueva | {sale.cliente_nombre or 'Sin Nombre'} | {sale.producto or 'S/P'}"
        
        msg.attach(MIMEText(html, 'html'))
        
        # 4. Send
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
            
        logger.info(f"Backoffice email sent for sale {sale.message_id}")
        return True
    except Exception as e:
        logger.error(f"Error sending backoffice email: {e}")
        return False

def build_sale_html(sale: SaleCreate):
    """Generates a rich HTML table for the sale."""
    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
    
    rows = [
        ("Agente", sale.agente),
        ("MessageId", sale.message_id),
        ("Producto", sale.producto),
        ("Tipo Venta", sale.tipo_venta),
        ("Fecha", now_str),
        ("---", "---"),
        ("Cliente", sale.cliente_nombre),
        ("Cédula", sale.cliente_cedula),
        ("Email", sale.cliente_email),
        ("Teléfono", sale.cliente_telefono),
        ("Nacimiento", sale.cliente_nacimiento),
        ("---", "---"),
        ("Departamento", sale.dir_depto),
        ("Ciudad", sale.dir_ciudad),
        ("Dirección", f"{sale.dir_calle} {sale.dir_puerta} {sale.dir_apto or ''}"),
        ("Esquinas", f"{sale.dir_esq1} / {sale.dir_esq2}"),
        ("---", "---"),
        ("Plan", sale.venta_plan),
        ("Equipo", sale.venta_equipo),
        ("Pago", sale.venta_pago),
        ("Precio", sale.venta_precio),
        ("Cuotas", sale.venta_cuotas),
        ("---", "---"),
        ("Envío", sale.envio_tipo),
        ("Detalle Envío", sale.envio_detalles),
        ("NIP (Porta)", sale.porta_nip),
        ("---", "---"),
        ("Comentarios", sale.vendedor_comentarios),
    ]
    
    table_rows = ""
    for k, v in rows:
        if k == "---":
            table_rows += '<tr><td colspan="2" style="background:#f1f5f9; height:1px; padding:0;"></td></tr>'
        else:
            table_rows += f"""
            <tr>
                <td style="padding:8px; border-bottom:1px solid #e2e8f0; color:#64748b; font-size:12px; width:140px;">{k}</td>
                <td style="padding:8px; border-bottom:1px solid #e2e8f0; color:#1e293b; font-size:12px; font-weight:600;">{v or '—'}</td>
            </tr>
            """
            
    return f"""
    <html>
    <body style="font-family:sans-serif; color:#334155; margin:0; padding:20px; background:#f8fafc;">
        <div style="max-width:600px; margin:0 auto; background:#fff; border-radius:12px; border:1px solid #e2e8f0; overflow:hidden; box-shadow:0 4px 6px -1px rgb(0 0 0 / 0.1);">
            <div style="background:#00aef0; padding:20px; color:#fff;">
                <h2 style="margin:0; font-size:18px;">📦 Nueva Venta Registrada</h2>
                <p style="margin:5px 0 0 0; font-size:12px; opacity:0.8;">Detalle para Backoffice</p>
            </div>
            <div style="padding:20px;">
                <table style="width:100%; border-collapse:collapse;">
                    {table_rows}
                </table>
            </div>
            <div style="background:#f8fafc; padding:15px; text-align:center; font-size:11px; color:#94a3b8; border-top:1px solid #e2e8f0;">
                Tigo Leads Bot • Generado automáticamente
            </div>
        </div>
    </body>
    </html>
    """
