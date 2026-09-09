"""Script manual para probar la primera llamada real a Gemini.

Uso:
    uv run python -m scripts.probar_gemini
"""
from app.models.schemas import ClasificacionOutput
from app.services.llm_service import llamar_llm_estructurado

CORREO_EJEMPLO = """
De: facturacion@electricidad-ejemplo.com
Asunto: Tu factura de agosto ya está disponible

Hola,

Tu factura de electricidad correspondiente a agosto de 2026 ya está
disponible. El monto a pagar es de $842 MXN, con vencimiento el 5 de
septiembre. Puedes consultarla en tu portal de cliente.

Gracias por tu preferencia.
"""

if __name__ == "__main__":
    prompt = f"""Eres un asistente que clasifica correos electrónicos.
Clasifica el siguiente correo en una de estas categorías: trabajo, personal,
facturas, promociones, spam, otros.

Correo:
{CORREO_EJEMPLO}
"""

    resultado: ClasificacionOutput = llamar_llm_estructurado(prompt, ClasificacionOutput)

    print("Respuesta de Gemini (ya validada por Pydantic):\n")
    print(resultado.model_dump_json(indent=2))