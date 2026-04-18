import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def send_2fa_email(to_email: str, codigo: str, nombre: str = ""):
    creds = Credentials(
        token=None,
        refresh_token=os.environ['GMAIL_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ['GMAIL_CLIENT_ID'],
        client_secret=os.environ['GMAIL_CLIENT_SECRET'],
        scopes=['https://www.googleapis.com/auth/gmail.send']
    )
    creds.refresh(Request())

    message = MIMEMultipart('alternative')
    message['to'] = to_email
    message['from'] = os.environ['GMAIL_SENDER_EMAIL']
    message['subject'] = '🔐 Tu código de verificación - MercaMax'

    saludo = f"Hola {nombre}," if nombre else "Hola,"

    message.attach(MIMEText(
        f"{saludo}\n\nTu código de verificación es: {codigo}\n\nExpira en 5 minutos.\n\nEquipo MercaMax.",
        'plain'
    ))
    message.attach(MIMEText(f"""
    <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
        
        <!-- Header -->
        <div style="background:#1a56db;padding:24px;text-align:center">
            <h1 style="color:white;margin:0;font-size:24px">🛒 MercaMax</h1>
            <p style="color:#bfdbfe;margin:4px 0 0">Sistema de Gestión de Inventarios</p>
        </div>

        <!-- Body -->
        <div style="padding:32px 24px;background:#ffffff">
            <p style="font-size:16px;color:#374151">{saludo}</p>
            <p style="color:#6b7280">Recibimos una solicitud de acceso a tu cuenta. Usa el siguiente código para continuar:</p>
            
            <!-- Código -->
            <div style="background:#f0f7ff;border:2px dashed #1a56db;border-radius:8px;padding:20px;text-align:center;margin:24px 0">
                <p style="margin:0;color:#6b7280;font-size:13px;text-transform:uppercase;letter-spacing:1px">Tu código de verificación</p>
                <h2 style="margin:8px 0 0;font-size:48px;letter-spacing:16px;color:#1a56db;font-weight:800">{codigo}</h2>
            </div>

            <p style="color:#ef4444;font-size:13px;text-align:center">⏱ Este código expira en <strong>5 minutos</strong></p>
            <p style="color:#6b7280;font-size:13px">Si no fuiste tú quien intentó ingresar, ignora este correo y considera cambiar tu contraseña.</p>
        </div>

        <!-- Footer -->
        <div style="background:#f9fafb;padding:16px 24px;text-align:center;border-top:1px solid #e2e8f0">
            <p style="margin:0;color:#9ca3af;font-size:12px">© 2026 MercaMax · Este es un correo automático, no respondas a este mensaje.</p>
        </div>

    </div>
    """, 'html'))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service = build('gmail', 'v1', credentials=creds)
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
    except HttpError as e:
        raise Exception(f"Error Gmail API: {e.status_code} - {e.reason}")
    
def send_factura_email(to_email: str, nombre: str, numero_factura: str, 
                        total: str, pdf_bytes: bytes):
    """Envía la factura PDF al correo del cliente."""
    from email.mime.base import MIMEBase
    from email import encoders

    creds = Credentials(
        token=None,
        refresh_token=os.environ['GMAIL_REFRESH_TOKEN'],
        token_uri='https://oauth2.googleapis.com/token',
        client_id=os.environ['GMAIL_CLIENT_ID'],
        client_secret=os.environ['GMAIL_CLIENT_SECRET'],
        scopes=['https://www.googleapis.com/auth/gmail.send']
    )
    creds.refresh(Request())

    message = MIMEMultipart('mixed')
    message['to'] = to_email
    message['from'] = os.environ['GMAIL_SENDER_EMAIL']
    message['subject'] = f'🧾 Tu factura {numero_factura} - MercaMax'

    saludo = f"Hola {nombre}," if nombre else "Hola,"

    # ── Cuerpo HTML ──────────────────────────────────────────
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">

        <div style="background:#27AE60;padding:24px;text-align:center">
            <h1 style="color:white;margin:0;font-size:24px">🛒 MercaMax</h1>
            <p style="color:#d4edda;margin:4px 0 0">Comprobante de compra</p>
        </div>

        <div style="padding:32px 24px;background:#ffffff">
            <p style="font-size:16px;color:#374151">{saludo}</p>
            <p style="color:#6b7280">Gracias por tu compra. Adjuntamos el comprobante de tu transacción:</p>

            <div style="background:#f0fff4;border:2px solid #27AE60;border-radius:8px;padding:20px;margin:24px 0">
                <p style="margin:0 0 6px;color:#6b7280;font-size:13px;text-transform:uppercase;letter-spacing:1px">N° Factura</p>
                <h2 style="margin:0 0 12px;font-size:28px;color:#27AE60;font-weight:800">{numero_factura}</h2>
                <p style="margin:0;color:#374151;font-size:15px">Total pagado: <strong style="color:#27AE60">{total}</strong></p>
            </div>

            <p style="color:#6b7280;font-size:13px">El PDF de tu factura está adjunto en este correo. Consérvalo como comprobante de pago.</p>
        </div>

        <div style="background:#f9fafb;padding:16px 24px;text-align:center;border-top:1px solid #e2e8f0">
            <p style="margin:0;color:#9ca3af;font-size:12px">© 2026 MercaMax · Este es un correo automático, no respondas a este mensaje.</p>
        </div>

    </div>
    """

    alt_part = MIMEMultipart('alternative')
    alt_part.attach(MIMEText(
        f"{saludo}\n\nGracias por tu compra en MercaMax.\nFactura: {numero_factura}\nTotal: {total}\n\nAdjuntamos el PDF de tu factura.",
        'plain'
    ))
    alt_part.attach(MIMEText(html, 'html'))
    message.attach(alt_part)

    # ── PDF adjunto ──────────────────────────────────────────
    adjunto = MIMEBase('application', 'pdf')
    adjunto.set_payload(pdf_bytes)
    encoders.encode_base64(adjunto)
    adjunto.add_header(
        'Content-Disposition',
        f'attachment; filename="{numero_factura}.pdf"'
    )
    message.attach(adjunto)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service = build('gmail', 'v1', credentials=creds)
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
    except HttpError as e:
        raise Exception(f"Error Gmail API: {e.status_code} - {e.reason}")