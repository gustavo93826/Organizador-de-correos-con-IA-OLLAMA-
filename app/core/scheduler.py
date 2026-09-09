"""Configuración del scheduler: qué job correr y con qué frecuencia.
"""
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from app.services.sync_service import sincronizar_correos_nuevos
from app.workflows.procesar_email import procesar_bandeja

# Ajusta estos dos valores según tu RPD real (ver tu dashboard de AI Studio).
INTERVALO_MINUTOS = 5
LIMITE_CORREOS_POR_CICLO = 10


def ciclo_completo() -> None:
    """Un ciclo completo: trae correos nuevos de Gmail y los procesa."""
    logger.info("Iniciando ciclo de sincronización y procesamiento...")
    try:
        nuevos = sincronizar_correos_nuevos(max_results=LIMITE_CORREOS_POR_CICLO)
        if nuevos > 0:
            procesar_bandeja(limite=LIMITE_CORREOS_POR_CICLO)
        else:
            logger.info("No hay correos nuevos, se omite el procesamiento.")
    except Exception:
        logger.exception("Error en el ciclo del scheduler.")


def crear_scheduler() -> BackgroundScheduler:
    """Crea (sin iniciar) el scheduler con el job configurado."""
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        ciclo_completo,
        trigger="interval",
        minutes=INTERVALO_MINUTOS,
        id="ciclo_correos",
        next_run_time=datetime.now(),  # primer ciclo inmediato; luego cada INTERVALO_MINUTOS
        replace_existing=True,
    )
    return scheduler