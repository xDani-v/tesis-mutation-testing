"""
Cliente centralizado para llamar a Gemini.
Todas las estrategias pasan por aqui - un solo lugar para cambiar
de modelo o proveedor si hace falta mas adelante.
"""
import os
import time
from google import genai
from google.genai import types

MODEL_NAME = "gemini-3.5-flash"

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "No se encontro GOOGLE_API_KEY ni GEMINI_API_KEY en el entorno. "
                "Exporta la variable antes de correr el script."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def generar_texto(prompt: str, temperature: float = 0.2) -> dict:
    """
    Llama al modelo con un prompt y devuelve el texto generado
    junto con metadatos utiles para tus metricas (tiempo, tokens).

    Retorna:
        {
            "texto": str,
            "tiempo_segundos": float,
            "tokens_entrada": int,
            "tokens_salida": int,
        }
    """
    client = _get_client()
    inicio = time.perf_counter()

    respuesta = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
        ),
    )

    tiempo_transcurrido = time.perf_counter() - inicio

    uso = respuesta.usage_metadata
    tokens_entrada = uso.prompt_token_count if uso else 0
    tokens_salida = uso.candidates_token_count if uso else 0

    return {
        "texto": respuesta.text or "",
        "tiempo_segundos": round(tiempo_transcurrido, 3),
        "tokens_entrada": tokens_entrada,
        "tokens_salida": tokens_salida,
    }


def extraer_codigo_python(texto_llm: str) -> str:
    """
    El LLM normalmente envuelve el codigo en bloques ```python ... ```.
    Esta funcion extrae solo el codigo, sin el markdown envolvente.
    """
    texto = texto_llm.strip()

    if "```python" in texto:
        inicio = texto.find("```python") + len("```python")
        fin = texto.find("```", inicio)
        return texto[inicio:fin].strip()

    if "```" in texto:
        inicio = texto.find("```") + 3
        fin = texto.find("```", inicio)
        return texto[inicio:fin].strip()

    return texto
