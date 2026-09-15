"""Endpoints REST para consultar y gestionar los correos procesados."""
from datetime import UTC, date, datetime, time
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger
from sqlmodel import Session, select

from app.api.schemas import ActualizarBorrador, EmailDetail, EmailListItem
from app.core.config import MAX_EMAILS
from app.core.database import get_session
from app.models.email import Categoria, Email, EstadoProcesamiento, Prioridad
from app.workflows.procesar_email import procesar_un_email

router = APIRouter(prefix="/emails", tags=["emails"])


@router.get("", response_model=list[EmailListItem])
def listar_emails(
    categoria: Categoria | None = None,
    prioridad: Prioridad | None = None,
    estado: EstadoProcesamiento | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
    session: Session = Depends(get_session),
):
    """Lista correos con filtros opcionales y rango inclusivo de fechas."""
    query = select(Email)
    if categoria:
        query = query.where(Email.categoria == categoria)
    if prioridad:
        query = query.where(Email.prioridad == prioridad)
    if estado:
        query = query.where(Email.estado_procesamiento == estado)
    if fecha_desde:
        query = query.where(
            Email.fecha_recibido >= datetime.combine(fecha_desde, time.min, tzinfo=UTC)
        )
    if fecha_hasta:
        query = query.where(
            Email.fecha_recibido <= datetime.combine(fecha_hasta, time.max, tzinfo=UTC)
        )

    query = query.order_by(Email.fecha_recibido.desc())
    return session.exec(query).all()

@router.get("/capacidad")
def consultar_capacidad(session: Session = Depends(get_session)):
    """Devuelve el uso de la bandeja y la cantidad de correos pendientes."""
    procesados = len(
        session.exec(
            select(Email.id).where(Email.estado_procesamiento == EstadoProcesamiento.COMPLETADO)
        ).all()
    )
    pendientes = len(
        session.exec(
            select(Email.id).where(Email.estado_procesamiento == EstadoProcesamiento.PENDIENTE)
        ).all()
    )
    return {
        "procesados": procesados,
        "pendientes": pendientes,
        "maximo": MAX_EMAILS,
        "limite_alcanzado": procesados >= MAX_EMAILS,
    }


@router.delete("")
def eliminar_todos_los_emails(session: Session = Depends(get_session)):
    """Elimina los correos completados, sin tocar los nuevos pendientes."""
    emails = session.exec(
        select(Email).where(Email.estado_procesamiento == EstadoProcesamiento.COMPLETADO)
    ).all()
    for email in emails:
        session.delete(email)
    session.commit()
    return {"mensaje": f"Se eliminaron {len(emails)} correo(s).", "eliminados": len(emails)}


@router.get("/{email_id}", response_model=EmailDetail)
def obtener_email(email_id: int, session: Session = Depends(get_session)):
    email = session.get(Email, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")
    return email

@router.delete("/{email_id}")
def eliminar_email(email_id: int, session: Session = Depends(get_session)):
    """Elimina un correo concreto por su identificador."""
    email = session.get(Email, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    session.delete(email)
    session.commit()
    return {"mensaje": f"Correo {email_id} eliminado.", "eliminado": email_id}


@router.patch("/{email_id}/borrador", response_model=EmailDetail)
def actualizar_borrador(
    email_id: int,
    datos: ActualizarBorrador,
    session: Session = Depends(get_session),
):
    """Permite editar manualmente el borrador de respuesta sugerido por la IA."""
    email = session.get(Email, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    email.borrador_respuesta = datos.borrador
    session.add(email)
    session.commit()
    session.refresh(email)
    return email


@router.post("/{email_id}/reprocesar", status_code=202)
def reprocesar_email(
    email_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Fuerza el reprocesamiento de un correo puntual, en segundo plano.

    A diferencia del scheduler del Paso 8 (que corre por intervalo fijo),
    esto usa BackgroundTasks de FastAPI para no bloquear la respuesta
    HTTP mientras el LLM procesa el correo (puede tardar varios segundos).
    """
    email = session.get(Email, email_id)
    if email is None:
        raise HTTPException(status_code=404, detail="Correo no encontrado")

    email.estado_procesamiento = EstadoProcesamiento.PROCESANDO
    session.add(email)
    session.commit()

    background_tasks.add_task(_reprocesar_en_segundo_plano, email_id)
    return {"mensaje": f"Reprocesamiento del correo {email_id} iniciado en segundo plano."}


def _reprocesar_en_segundo_plano(email_id: int) -> None:
    """Wrapper para BackgroundTasks.

    `procesar_un_email` ya deja el correo en estado ERROR y relanza la
    excepción (para que Prefect y el scheduler se enteren del fallo).
    Como nadie más va a capturarla, se registra con logging
    en vez de dejar que Starlette la reporte como un traceback crudo.
    """
    try:
        procesar_un_email(email_id)
    except Exception:
        logger.exception(f"Reprocesamiento en segundo plano falló para el correo {email_id}.")