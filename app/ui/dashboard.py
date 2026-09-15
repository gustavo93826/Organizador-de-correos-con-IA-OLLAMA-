"""Interfaz Streamlit: bandeja organizada por categoría/prioridad, con
resumen visible y borrador de respuesta editable.

Consume la API de FastAPI vía HTTP -- no accede a la base de
datos directamente, para mantener una única fuente de verdad.

Uso:
    uv run streamlit run app/ui/dashboard.py
"""
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
ZONA_HORARIA = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Caracas"))

EMOJI_PRIORIDAD = {"alta": "🔴", "media": "🟡", "baja": "🟢", None: "⚪"}

st.set_page_config(page_title="Organizador de correos con IA", layout="wide")
st.title("📬 Organizador de correos con IA")


def obtener_emails(categoria, prioridad, estado, fecha_desde, fecha_hasta) -> list[dict]:
    params = {
        k: v
        for k, v in {
            "categoria": categoria,
            "prioridad": prioridad,
            "estado": estado,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
        }.items()
        if v
    }
    respuesta = requests.get(f"{API_BASE_URL}/emails", params=params, timeout=10)
    respuesta.raise_for_status()
    return respuesta.json()

def obtener_capacidad() -> dict:
    respuesta = requests.get(f"{API_BASE_URL}/emails/capacidad", timeout=10)
    respuesta.raise_for_status()
    return respuesta.json()


def obtener_detalle(email_id: int) -> dict:
    respuesta = requests.get(f"{API_BASE_URL}/emails/{email_id}", timeout=10)
    respuesta.raise_for_status()
    return respuesta.json()


def guardar_borrador(email_id: int, texto: str) -> None:
    respuesta = requests.patch(
        f"{API_BASE_URL}/emails/{email_id}/borrador", json={"borrador": texto}, timeout=10
    )
    respuesta.raise_for_status()


def reprocesar(email_id: int) -> None:
    respuesta = requests.post(f"{API_BASE_URL}/emails/{email_id}/reprocesar", timeout=10)
    respuesta.raise_for_status()


def borrar_email(email_id: int) -> None:
    respuesta = requests.delete(f"{API_BASE_URL}/emails/{email_id}", timeout=10)
    respuesta.raise_for_status()


def borrar_todos_los_emails() -> None:
    respuesta = requests.delete(f"{API_BASE_URL}/emails", timeout=10)
    respuesta.raise_for_status()


# --- Filtros en la barra lateral ---
st.sidebar.header("Filtros")
categoria = st.sidebar.selectbox(
    "Categoría",
    ["", "trabajo", "personal", "facturas", "promociones", "spam", "otros"],
    format_func=lambda v: "Todas" if v == "" else v.capitalize(),
)
prioridad = st.sidebar.selectbox(
    "Prioridad",
    ["", "alta", "media", "baja"],
    format_func=lambda v: "Todas" if v == "" else v.capitalize(),
)
estado = st.sidebar.selectbox(
    "Estado",
    ["completado", "", "pendiente", "procesando", "error"],
    format_func=lambda v: "Todos" if v == "" else v.capitalize(),
)
fecha_desde = st.sidebar.date_input("Recibidos desde", value=None)
fecha_hasta = st.sidebar.date_input("Recibidos hasta", value=None)

if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
    st.sidebar.error("La fecha inicial no puede ser posterior a la fecha final.")
    st.stop()

if st.sidebar.button("🔄 Actualizar"):
    st.rerun()
    
if st.sidebar.button("🗑️ Borrar todos los correos", type="secondary"):
    st.session_state["confirmar_borrado_todos"] = True

if st.session_state.get("confirmar_borrado_todos", False):
    st.sidebar.warning(
        "Esta acción eliminará permanentemente todos los correos procesados. "
        "¿Deseas continuar?"
    )
    confirmar_todos, cancelar_todos = st.sidebar.columns(2)
    with confirmar_todos:
        if st.button("Sí, borrar todos", key="confirmar_todos", type="primary"):
            borrar_todos_los_emails()
            st.session_state["confirmar_borrado_todos"] = False
            st.sidebar.success("Todos los correos procesados fueron eliminados.")
            st.rerun()
    with cancelar_todos:
        if st.button("Cancelar", key="cancelar_todos"):
            st.session_state["confirmar_borrado_todos"] = False
            st.rerun()

# --- Cuerpo principal ---
try:
    capacidad = obtener_capacidad()
    emails = obtener_emails(
        categoria or None,
        prioridad or None,
        estado or None,
        fecha_desde.isoformat() if isinstance(fecha_desde, date) else None,
        fecha_hasta.isoformat() if isinstance(fecha_hasta, date) else None,
    )
except requests.exceptions.ConnectionError:
    st.error(
        "No se pudo conectar con la API. ¿Está corriendo? "
        "`uv run uvicorn app.main:app --reload`"
    )
    st.stop()
    

st.caption(f"{capacidad['pendientes']} correo(s) nuevo(s) detectado(s)")

if capacidad["limite_alcanzado"]:
    st.warning(
        f"Has llegado al límite de {capacidad['maximo']} correos. "
        "Borra alguno para que puedan entrar nuevos correos."
    )


if not emails:
    st.info("No hay correos que coincidan con estos filtros.")
    st.stop()


for item in emails:
    detalle = obtener_detalle(item["id"])
    emoji = EMOJI_PRIORIDAD.get(detalle["prioridad"], "⚪")

    titulo = f"{emoji} {detalle['asunto']} — {detalle['remitente']}"
    with st.expander(titulo):
        col_info, col_estado = st.columns([3, 1])
        with col_info:
            fecha = datetime.fromisoformat(detalle["fecha_recibido"])
            st.write(f"**Fecha y hora:** {fecha.astimezone(ZONA_HORARIA).strftime('%d/%m/%Y %H:%M')}")
            st.write(f"**Categoría:** {detalle['categoria'] or '—'}")
            st.write(f"**Resumen:** {detalle['resumen'] or '(sin resumen aún)'}")
        with col_estado:
            st.write(f"**Estado:** {detalle['estado_procesamiento']}")

        borrador_editado = st.text_area(
            "Borrador de respuesta",
            value=detalle["borrador_respuesta"] or "",
            key=f"borrador_{detalle['id']}",
            height=120,
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Guardar borrador", key=f"guardar_{detalle['id']}"):
                guardar_borrador(detalle["id"], borrador_editado)
                st.success("Borrador actualizado.")
        with col2:
            if st.button("🔁 Reprocesar con IA", key=f"reprocesar_{detalle['id']}"):
                reprocesar(detalle["id"])
                st.info("Reprocesamiento iniciado en segundo plano.")
                st.rerun()

        if st.button("🗑️ Borrar correo", key=f"borrar_{detalle['id']}"):
            st.session_state[f"mostrar_confirmacion_{detalle['id']}"] = True

        if st.session_state.get(f"mostrar_confirmacion_{detalle['id']}", False):
            st.warning(
                "Este correo se eliminará permanentemente. "
                "¿Deseas continuar?"
            )
            confirmar, cancelar = st.columns(2)
            with confirmar:
                if st.button(
                    "Sí, borrar correo",
                    key=f"confirmar_borrado_btn_{detalle['id']}",
                    type="primary",
                ):
                    borrar_email(detalle["id"])
                    st.session_state[f"mostrar_confirmacion_{detalle['id']}"] = False
                    st.success("Correo eliminado.")
                    st.rerun()
            with cancelar:
                if st.button("Cancelar", key=f"cancelar_borrado_{detalle['id']}"):
                    st.session_state[f"mostrar_confirmacion_{detalle['id']}"] = False
                    st.rerun()