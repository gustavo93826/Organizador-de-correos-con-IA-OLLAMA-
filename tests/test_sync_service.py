"""Pruebas del límite de almacenamiento durante la sincronización."""
from datetime import UTC, datetime

from sqlmodel import Session, select

from app.models.email import Email
from app.services import sync_service


def _crear_email(session: Session, numero: int) -> None:
    session.add(
        Email(
            gmail_id=f"existente-{numero}",
            remitente="alguien@ejemplo.com",
            asunto=f"Correo {numero}",
            cuerpo="Cuerpo de prueba",
            fecha_recibido=datetime.now(UTC),
        )
    )


def test_sincronizacion_guarda_nuevos_como_pendientes(engine_test, monkeypatch):
    with Session(engine_test) as session:
        for numero in range(20):
            _crear_email(session, numero)
        session.commit()

    monkeypatch.setattr(sync_service, "engine", engine_test)
    monkeypatch.setattr(sync_service, "get_gmail_service", lambda: object())
    monkeypatch.setattr(
        sync_service,
        "obtener_mensajes_nuevos",
        lambda service, max_results: [
            {
                "gmail_id": "nuevo",
                "remitente": "nuevo@ejemplo.com",
                "asunto": "Nuevo correo",
                "cuerpo": "Contenido",
                "fecha_recibido": datetime.now(UTC),
            }
        ],
    )

    assert sync_service.sincronizar_correos_nuevos() == 1

    with Session(engine_test) as session:
        emails = session.exec(select(Email)).all()
        assert len(emails) == 21
        nuevo = next(email for email in emails if email.gmail_id == "nuevo")
        assert nuevo.estado_procesamiento.value == "pendiente"