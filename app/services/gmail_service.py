"""Servicio de autenticación y acceso a la API de Gmail.

Implementa el flujo OAuth2 "installed app" y funciones para leer
correos, incluyendo su cuerpo de texto completo.
"""
import base64
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from loguru import logger

from app.core.config import settings

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    """Devuelve un cliente autenticado de la API de Gmail."""
    creds = None
    token_path = settings.gmail_token_path

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expirado, refrescando...")
            creds.refresh(Request())
        else:
            if not settings.gmail_credentials_path.exists():
                logger.error(
                    f"No se encontró '{settings.gmail_credentials_path}'. "
                    "Descárgalo desde Google Cloud Console y colócalo en la raíz del proyecto."
                )
                raise FileNotFoundError(
                    f"Falta el archivo de credenciales de Gmail: {settings.gmail_credentials_path}"
                )
            logger.info("No hay token válido, iniciando flujo de consentimiento OAuth2...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(settings.gmail_credentials_path), SCOPES
            )
            creds = flow.run_local_server(port=0)

        token_path.write_text(creds.to_json())
        logger.info(f"Token guardado en {token_path}")

    return build("gmail", "v1", credentials=creds)


def list_recent_messages(service, max_results: int = 5) -> list[dict]:
    """Últimos correos con remitente y asunto (sin cuerpo). Se conserva
    del Paso 2 para pruebas rápidas de conexión.
    """
    response = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=max_results
    ).execute()

    messages = []
    for msg_ref in response.get("messages", []):
        msg = service.users().messages().get(
            userId="me", id=msg_ref["id"], format="metadata",
            metadataHeaders=["Subject", "From"],
        ).execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        messages.append({
            "id": msg["id"],
            "from": headers.get("From", "(desconocido)"),
            "subject": headers.get("Subject", "(sin asunto)"),
        })
    return messages


def obtener_mensajes_nuevos(service, max_results: int = 10) -> list[dict]:
    """Correos más recientes con remitente, asunto, cuerpo de texto y
    fecha, listos para guardar directamente en el modelo `Email`.
    """
    response = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=max_results
    ).execute()

    mensajes = []
    for ref in response.get("messages", []):
        msg = service.users().messages().get(userId="me", id=ref["id"], format="full").execute()
        headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
        cuerpo = _extraer_cuerpo_texto(msg["payload"])
        fecha = datetime.fromtimestamp(int(msg["internalDate"]) / 1000, tz=timezone.utc)

        mensajes.append({
            "gmail_id": msg["id"],
            "remitente": headers.get("From", "(desconocido)"),
            "asunto": headers.get("Subject", "(sin asunto)"),
            "cuerpo": cuerpo,
            "fecha_recibido": fecha,
        })
    return mensajes


def _extraer_cuerpo_texto(payload: dict) -> str:
    """Recorre las partes MIME del mensaje y devuelve el texto plano.
    Si no hay text/plain, cae a la primera parte con contenido disponible.
    """
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return _decodificar_base64url(payload["body"]["data"])

    partes = payload.get("parts") or []

    for parte in partes:
        if parte.get("mimeType") == "text/plain" and "data" in parte.get("body", {}):
            return _decodificar_base64url(parte["body"]["data"])

    for parte in partes:
        if "data" in parte.get("body", {}):
            return _decodificar_base64url(parte["body"]["data"])
        if parte.get("parts"):
            resultado = _extraer_cuerpo_texto(parte)
            if resultado:
                return resultado

    return "(no se pudo extraer el contenido del correo)"


def _decodificar_base64url(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")