# Organizador de correos con IA

Aplicación que se conecta a Gmail y organiza automáticamente la bandeja usando un LLM:
clasifica, resume, prioriza y sugiere borradores de respuesta.

## Estado del proyecto

- [x] Paso 1 — Preparación del entorno y accesos
- [x] Paso 2 — Conexión y autenticación con Gmail
- [x] Paso 3 — Modelo de datos y base de datos
- [x] Paso 4 — Esquemas de salida estructurada del LLM
- [x] Paso 5 — Primera integración con Ollama
- [x] Paso 6 — Las 4 funciones de IA como piezas independientes
- [x] Paso 7 — Orquestación del workflow con Prefect
- [x] Paso 8 — Automatización con APScheduler
- [x] Paso 9 — Capa de API con FastAPI
- [x] Paso 10 — Interfaz de usuario con Streamlit
- [x] Paso 11 — Testing
- [x] Paso 12 — Logging y manejo de errores robusto
- [x] Paso 13 — Containerización con Docker

## Stack

Python 3.12 · FastAPI · Ollama (local, sin API key) · Pydantic · SQLite + SQLModel ·
APScheduler · Prefect · tenacity · Loguru · Streamlit · uv · Docker · Render