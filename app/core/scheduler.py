"""Configuración del scheduler: qué job correr y con qué frecuencia.
"""
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.services.sync_service import sincronizar_correos_nuevos
from app.workflows.procesar_email import procesar_bandeja

# Ajusta estos dos valores según tu RPD real (ver tu dashboard de AI Studio).
INTERVALO_MINUTOS = 5
INTERVALO_DETECCION_MINUTOS = 5
LIMITE_CORREOS_POR_CICLO = 10
LIMITE_CORREOS_A_DETECTAR = 20


def ciclo_deteccion() -> None:
    """Consulta Gmail y guarda los mensajes nuevos como pendientes."""
    logger.info("Iniciando ciclo de detección de correos...")
    try:
        nuevos = sincronizar_correos_nuevos(max_results=LIMITE_CORREOS_A_DETECTAR)
        if nuevos == 0:
            logger.info("No hay correos nuevos detectados.")
    except Exception:
        logger.exception("Error en el ciclo de detección.")


def ciclo_procesamiento() -> None:
    """Procesa los correos pendientes respetando el límite de la bandeja."""
    logger.info("Iniciando ciclo de procesamiento...")
    try:
        procesar_bandeja(limite=LIMITE_CORREOS_POR_CICLO)
    except Exception:
        logger.exception("Error en el ciclo de procesamiento.")


def crear_scheduler() -> BackgroundScheduler:
    """Crea (sin iniciar) el scheduler con dos jobs independientes."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        ciclo_deteccion,
        trigger="interval",
        minutes=INTERVALO_DETECCION_MINUTOS,
        id="deteccion_correos",
        next_run_time=datetime.now(),
        replace_existing=True,
    )
    scheduler.add_job(
        ciclo_procesamiento,
        trigger="interval",
        minutes=INTERVALO_MINUTOS,
        id="procesamiento_correos",
        next_run_time=datetime.now(),
        replace_existing=True,
    )
    return scheduler