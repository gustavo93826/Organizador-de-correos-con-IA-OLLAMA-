"""Pruebas de integración de los endpoints de la API."""
from datetime import UTC, datetime

from sqlmodel import Session

from app.models.email import Categoria, Email, EstadoProcesamiento, Prioridad


def _crear_email(session: Session, **overrides) -> Email:
    datos = {
        "gmail_id": "test-api-001",
        "remitente": "alguien@ejemplo.com",
        "asunto": "Correo de prueba",
        "cuerpo": "Cuerpo de prueba",
        "fecha_recibido": datetime.now(UTC),
        "estado_procesamiento": EstadoProcesamiento.COMPLETADO,
        "categoria": Categoria.TRABAJO,
        "prioridad": Prioridad.ALTA,
        "resumen": "Un resumen de prueba.",
        "borrador_respuesta": "Borrador original.",
    }
    datos.update(overrides)
    email = Email(**datos)
    session.add(email)
    session.commit()
    session.refresh(email)
    return email


def test_listar_emails_vacio(client):
    respuesta = client.get("/emails")
    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_consultar_capacidad(client, session):
    _crear_email(session)

    respuesta = client.get("/emails/capacidad")

    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "procesados": 1,
        "pendientes": 0,
        "maximo": 20,
        "limite_alcanzado": False,
    }



def test_listar_emails_con_datos(client, session):
    _crear_email(session)
    respuesta = client.get("/emails")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["asunto"] == "Correo de prueba"


def test_listar_emails_filtra_por_categoria(client, session):
    _crear_email(session, gmail_id="a", categoria=Categoria.TRABAJO)
    _crear_email(session, gmail_id="b", categoria=Categoria.PROMOCIONES)

    respuesta = client.get("/emails", params={"categoria": "trabajo"})
    datos = respuesta.json()
    assert len(datos) == 1
    assert datos[0]["categoria"] == "trabajo"


def test_obtener_email_no_encontrado(client):
    respuesta = client.get("/emails/999")
    assert respuesta.status_code == 404


def test_listar_emails_filtra_por_rango_de_fechas(client, session):
    _crear_email(session, gmail_id="antes", fecha_recibido=datetime(2026, 1, 10, tzinfo=UTC))
    _crear_email(session, gmail_id="dentro", fecha_recibido=datetime(2026, 1, 15, tzinfo=UTC))
    _crear_email(session, gmail_id="despues", fecha_recibido=datetime(2026, 1, 20, tzinfo=UTC))

    respuesta = client.get(
        "/emails",
        params={"fecha_desde": "2026-01-15", "fecha_hasta": "2026-01-15"},
    )

    datos = respuesta.json()
    assert respuesta.status_code == 200
    assert len(datos) == 1
    assert datos[0]["asunto"] == "Correo de prueba"
    assert datos[0]["fecha_recibido"].startswith("2026-01-15")


def test_actualizar_borrador(client, session):
    email = _crear_email(session)
    respuesta = client.patch(
        f"/emails/{email.id}/borrador", json={"borrador": "Nuevo borrador editado a mano."}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["borrador_respuesta"] == "Nuevo borrador editado a mano."


def test_reprocesar_email(client, session, mocker):
    email = _crear_email(session, estado_procesamiento=EstadoProcesamiento.COMPLETADO)

    mock_procesar = mocker.patch("app.api.emails.procesar_un_email")

    respuesta = client.post(f"/emails/{email.id}/reprocesar")
    assert respuesta.status_code == 202
    mock_procesar.assert_called_once_with(email.id)
    

def test_manejador_global_de_errores(client):
    from app.core.database import get_session
    from app.main import app

    def sesion_rota():
        raise RuntimeError("Fallo simulado de base de datos")

    app.dependency_overrides[get_session] = sesion_rota

    respuesta = client.get("/emails")
    assert respuesta.status_code == 500
    assert respuesta.json()["detail"].startswith("Ocurrió un error interno")
    
    
def test_eliminar_email(client, session):
    email = _crear_email(session)

    respuesta = client.delete(f"/emails/{email.id}")

    assert respuesta.status_code == 200
    assert respuesta.json()["eliminado"] == email.id
    assert client.get(f"/emails/{email.id}").status_code == 404


def test_eliminar_email_no_encontrado(client):
    respuesta = client.delete("/emails/999")
    assert respuesta.status_code == 404


def test_eliminar_todos_los_emails(client, session):
    _crear_email(session, gmail_id="a")
    _crear_email(session, gmail_id="b")
    _crear_email(
        session,
        gmail_id="pendiente",
        estado_procesamiento=EstadoProcesamiento.PENDIENTE,
    )

    respuesta = client.delete("/emails")

    assert respuesta.status_code == 200
    assert respuesta.json()["eliminados"] == 2
    correos_restantes = client.get("/emails").json()
    assert len(correos_restantes) == 1
    assert correos_restantes[0]["estado_procesamiento"] == "pendiente"


def test_eliminar_todos_los_emails_sin_datos(client):
    respuesta = client.delete("/emails")

    assert respuesta.status_code == 200
    assert respuesta.json()["eliminados"] == 0