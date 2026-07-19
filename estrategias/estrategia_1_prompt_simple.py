"""
Estrategia 1: Prompting tradicional.
Le pide al LLM que genere tests de una sola vez, sin corregir errores
ni usar retroalimentacion de mutation testing.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.llm_client import generar_texto, extraer_codigo_python
from shared.metricas import preparar_copia_proyecto, reemplazar_tests, correr_pytest, correr_mutmut


PROMPT_TEMPLATE = """Eres un ingeniero de software experto en testing con pytest.

Genera pruebas unitarias completas en pytest para el siguiente codigo Python.
El codigo pertenece a una API REST hecha con FastAPI y SQLAlchemy.

Requisitos:
- Usa pytest puro (no unittest).
- Cubre casos normales, casos borde y casos de error.
- Si el codigo usa una sesion de base de datos (Session), asume que existe
  un fixture llamado `db_session` que provee una sesion SQLAlchemy valida
  conectada a una base de datos SQLite en memoria ya inicializada.
- NO expliques nada fuera del codigo. Responde SOLO con un bloque de codigo
  Python que empiece con los imports necesarios.
- El archivo debe poder ejecutarse tal cual con `pytest`.

Codigo a probar (archivo: {nombre_archivo}):

```python
{codigo_fuente}
```
"""


def generar_tests_estrategia_1(codigo_fuente: str, nombre_archivo: str) -> dict:
    prompt = PROMPT_TEMPLATE.format(
        nombre_archivo=nombre_archivo, codigo_fuente=codigo_fuente
    )
    resultado_llm = generar_texto(prompt)
    codigo_test = extraer_codigo_python(resultado_llm["texto"])

    return {
        "codigo_test": codigo_test,
        "tiempo_generacion_segundos": resultado_llm["tiempo_segundos"],
        "tokens_entrada": resultado_llm["tokens_entrada"],
        "tokens_salida": resultado_llm["tokens_salida"],
    }


def ejecutar(sujeto_dir: str, archivo_fuente: str, carpeta_salida: str):
    """
    sujeto_dir: carpeta del proyecto sujeto, ej. 'sujetos/api-tareas'
    archivo_fuente: archivo a testear, ej. 'services.py'
    carpeta_salida: donde se copia el proyecto con los tests generados
    """
    sujeto_path = Path(sujeto_dir)
    destino_path = Path(carpeta_salida)

    codigo_fuente = (sujeto_path / archivo_fuente).read_text(encoding="utf-8")

    print(f"[Estrategia 1] Generando tests para {archivo_fuente}...")
    resultado_generacion = generar_tests_estrategia_1(codigo_fuente, archivo_fuente)

    print(f"[Estrategia 1] Preparando copia del proyecto en {destino_path}...")
    preparar_copia_proyecto(sujeto_path, destino_path)
    reemplazar_tests(destino_path, resultado_generacion["codigo_test"])

    print("[Estrategia 1] Corriendo pytest...")
    resultado_pytest = correr_pytest(destino_path)

    resultado_mutmut = None
    if resultado_pytest["compila"] and resultado_pytest["tests_passed"] > 0:
        print("[Estrategia 1] Corriendo mutmut (esto puede tardar)...")
        resultado_mutmut = correr_mutmut(destino_path)
    else:
        print("[Estrategia 1] Los tests no compilan o no pasan ninguno; se omite mutmut.")

    reporte = {
        "estrategia": "1_prompt_simple",
        "archivo_fuente": archivo_fuente,
        "generacion": resultado_generacion,
        "pytest": resultado_pytest,
        "mutmut": resultado_mutmut,
    }
    return reporte


if __name__ == "__main__":
    import json

    reporte = ejecutar(
        sujeto_dir="sujetos/api-tareas",
        archivo_fuente="services.py",
        carpeta_salida="resultados/api-tareas_estrategia1",
    )

    reporte_sin_salida_cruda = json.loads(json.dumps(reporte, default=str))
    if reporte_sin_salida_cruda.get("pytest", {}).get("salida_cruda"):
        del reporte_sin_salida_cruda["pytest"]["salida_cruda"]

    print("\n=== REPORTE ===")
    print(json.dumps(reporte_sin_salida_cruda, indent=2, ensure_ascii=False))

    Path("resultados").mkdir(exist_ok=True)
    with open("resultados/reporte_estrategia1.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False, default=str)
