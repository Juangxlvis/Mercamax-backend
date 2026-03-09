import base64
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def send_2fa_email(to_email: str, codigo: str):
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
    message['subject'] = 'Tu código de verificación'

    message.attach(MIMEText(f"Tu código 2FA es: {codigo}\nExpira en 10 minutos.", 'plain'))
    message.attach(MIMEText(f"""
        <div style="font-family:Arial,sans-serif;padding:20px;max-width:400px">
            <h2>Verificación en dos pasos</h2>
            <p>Tu código es:</p>
            <h1 style="letter-spacing:10px;color:#2563eb;font-size:40px">{codigo}</h1>
            <p style="color:#666">Expira en 10 minutos. No lo compartas.</p>
        </div>
    """, 'html'))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    try:
        service = build('gmail', 'v1', credentials=creds)
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
    except HttpError as e:
        raise Exception(f"Error Gmail API: {e.status_code} - {e.reason}")
