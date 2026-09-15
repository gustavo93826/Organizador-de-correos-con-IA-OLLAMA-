"""Pruebas de los ciclos independientes del scheduler."""
from app.core import scheduler


def test_crear_scheduler_configura_deteccion_y_procesamiento():
    scheduler_configurado = scheduler.crear_scheduler()

    trabajos = {trabajo.id: trabajo for trabajo in scheduler_configurado.get_jobs()}

    assert trabajos["deteccion_correos"].trigger.interval.total_seconds() == 5 * 60
    assert trabajos["procesamiento_correos"].trigger.interval.total_seconds() == 5 * 60


def test_ciclo_deteccion_no_procesa(monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        scheduler, "sincronizar_correos_nuevos", lambda max_results: llamadas.append(max_results) or 2
    )
    monkeypatch.setattr(
        scheduler,
        "procesar_bandeja",
        lambda limite: (_ for _ in ()).throw(AssertionError("no debe procesar")),
    )

    scheduler.ciclo_deteccion()

    assert llamadas == [scheduler.LIMITE_CORREOS_A_DETECTAR]


def test_ciclo_procesamiento_no_detecta(monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "sincronizar_correos_nuevos",
        lambda max_results: (_ for _ in ()).throw(AssertionError("no debe detectar")),
    )
    llamadas = []
    monkeypatch.setattr(scheduler, "procesar_bandeja", lambda limite: llamadas.append(limite))

    scheduler.ciclo_procesamiento()

    assert llamadas == [scheduler.LIMITE_CORREOS_POR_CICLO]
