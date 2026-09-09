"""Servicio de integración con el LLM (Ollama, local).

Centraliza el cliente de Ollama y la función genérica para pedir
salidas estructuradas, validadas con un esquema Pydantic.
"""
from loguru import logger
from ollama import Client, ResponseError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings

_client: Client | None = None


def get_ollama_client() -> Client:
    """Devuelve un cliente de Ollama reutilizable (lazy singleton)."""
    global _client
    if _client is None:
        _client = Client(host=settings.ollama_host)
    return _client


def _es_error_reintentable(exc: BaseException) -> bool:
    """True si el error es transitorio y vale la pena reintentar.

    - ConnectionError: Ollama todavía no responde (recién arrancando,
      o cargando el modelo en memoria por primera vez). Reintentar.
    - ResponseError con status_code >= 500: error transitorio del
      servidor. Reintentar.
    - Cualquier otro caso (p. ej. 404 porque el modelo no existe): no
      tiene sentido reintentar, es un problema de configuración.
    """
    if isinstance(exc, ConnectionError):
        return True
    if isinstance(exc, ResponseError):
        return exc.status_code >= 500
    return False


@retry(
    retry=retry_if_exception(_es_error_reintentable),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(5),
    reraise=True,
)
def llamar_llm_estructurado(prompt: str, esquema: type[BaseModel]) -> BaseModel:
    """Llama a Ollama pidiendo una respuesta que cumpla `esquema`.

    Usa el parámetro `format` de Ollama (JSON Schema) para forzar una
    salida estructurada -- el mismo rol que cumplía `response_schema`
    en Gemini. El contrato con `ia_service.py` no cambia.
    """
    client = get_ollama_client()

    logger.debug(f"Llamando a Ollama ({settings.ollama_model}) con esquema {esquema.__name__}...")

    respuesta = client.chat(
        model=settings.ollama_model,
        messages=[{"role": "user", "content": prompt}],
        format=esquema.model_json_schema(),
        options={"temperature": 0},
    )

    contenido = respuesta.message.content
    if not contenido:
        raise ValueError(f"Ollama no devolvió contenido para el esquema {esquema.__name__}.")

    return esquema.model_validate_json(contenido)