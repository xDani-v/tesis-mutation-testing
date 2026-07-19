"""
Estrategia 2: Ciclo iterativo de correccion.
Genera tests, y si fallan (error de sintaxis, import, aserciones rotas),
le devuelve el error real al LLM para que los corrija, hasta un maximo
de intentos.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.llm_client import generar_texto, extraer_codigo_python
from shared.metricas import preparar_copia_proyecto, reemplazar_tests, correr_pytest, correr_mutmut


PROMPT_INICIAL = """Eres un ingeniero de software experto en testing con pytest.

Genera pruebas unitarias completas en pytest para el siguiente codigo Python.
El codigo pertenece a una API REST hecha con FastAPI y SQLAlchemy.

Requisitos:
- Usa pytest puro (no unittest).
- Cubre casos normales, casos borde y casos de error.
- Si el codigo usa una sesion de base de datos (Session), asume que existe
  un fixture llamado db_session que provee una sesion SQLAlchemy valida
  conectada a una base de datos SQLite en memoria ya inicializada.
- NO expliques nada fuera del codigo. Responde SOLO con un bloque de codigo
  Python que empiece con los imports necesarios.
- El archivo debe poder ejecutarse tal cual con pytest.
- IMPORTANTE: Debes importar las funciones, clases y modelos directamente
  desde el modulo original usando 'from {nombre_archivo_sin_ext} import ...'. 
  NUNCA redefinas, copies o reimplementes el codigo fuente, los modelos
  SQLAlchemy, ni los schemas Pydantic dentro del archivo de test. El
  archivo de test debe depender del modulo real para que las pruebas
  reflejen fielmente su comportamiento.

Codigo a probar (archivo: {nombre_archivo}):

CODIGO_FUENTE_AQUI
{codigo_fuente}
FIN_CODIGO_FUENTE
"""

PROMPT_CORRECCION = """El siguiente codigo de tests en pytest fallo al ejecutarse.

Codigo de test actual:
CODIGO_TEST_AQUI
{codigo_test}
FIN_CODIGO_TEST

Error obtenido al correr pytest:
ERROR_AQUI
{error_pytest}
FIN_ERROR

Corrige el codigo de test para que se ejecute correctamente y siga
cubriendo los mismos casos de prueba. Responde SOLO con el bloque de
codigo Python corregido completo, sin explicaciones fuera del codigo.
"""

MAX_INTENTOS = 3


def generar_tests_estrategia_2(
    codigo_fuente: str, nombre_archivo: str, sujeto_dir: Path, destino_dir: Path
) -> dict:
    nombre_modulo = nombre_archivo.replace(".py", "")
    prompt = PROMPT_INICIAL.format(
        nombre_archivo=nombre_archivo, codigo_fuente=codigo_fuente,
        nombre_archivo_sin_ext=nombre_modulo
    )

    tiempo_total = 0.0
    tokens_entrada_total = 0
    tokens_salida_total = 0
    historial_intentos = []

    resultado_llm = generar_texto(prompt)
    codigo_test = extraer_codigo_python(resultado_llm["texto"])
    tiempo_total += resultado_llm["tiempo_segundos"]
    tokens_entrada_total += resultado_llm["tokens_entrada"]
    tokens_salida_total += resultado_llm["tokens_salida"]

    for intento in range(1, MAX_INTENTOS + 1):
        preparar_copia_proyecto(sujeto_dir, destino_dir)
        reemplazar_tests(destino_dir, codigo_test)
        resultado_pytest = correr_pytest(destino_dir)

        historial_intentos.append({
            "intento": intento,
            "compila": resultado_pytest["compila"],
            "tests_passed": resultado_pytest["tests_passed"],
            "tests_failed": resultado_pytest["tests_failed"],
            "tests_error": resultado_pytest["tests_error"],
        })

        exito = (
            resultado_pytest["compila"]
            and resultado_pytest["tests_error"] == 0
            and resultado_pytest["tests_failed"] == 0
            and resultado_pytest["tests_passed"] > 0
        )

        if exito or intento == MAX_INTENTOS:
            break

        print(f"  [Intento {intento}] Los tests fallaron, pidiendo correccion al LLM...")
        prompt_correccion = PROMPT_CORRECCION.format(
            codigo_test=codigo_test,
            error_pytest=resultado_pytest["salida_cruda"],
        )
        resultado_llm = generar_texto(prompt_correccion)
        codigo_test = extraer_codigo_python(resultado_llm["texto"])
        tiempo_total += resultado_llm["tiempo_segundos"]
        tokens_entrada_total += resultado_llm["tokens_entrada"]
        tokens_salida_total += resultado_llm["tokens_salida"]

    return {
        "codigo_test": codigo_test,
        "intentos_usados": len(historial_intentos),
        "historial_intentos": historial_intentos,
        "tiempo_generacion_segundos": round(tiempo_total, 3),
        "tokens_entrada": tokens_entrada_total,
        "tokens_salida": tokens_salida_total,
        "resultado_pytest_final": resultado_pytest,
    }


def ejecutar(sujeto_dir: str, archivo_fuente: str, carpeta_salida: str):
    sujeto_path = Path(sujeto_dir)
    destino_path = Path(carpeta_salida)

    codigo_fuente = (sujeto_path / archivo_fuente).read_text(encoding="utf-8")

    print(f"[Estrategia 2] Generando tests para {archivo_fuente} (con correccion iterativa)...")
    resultado_generacion = generar_tests_estrategia_2(
        codigo_fuente, archivo_fuente, sujeto_path, destino_path
    )

    resultado_pytest = resultado_generacion.pop("resultado_pytest_final")

    resultado_mutmut = None
    if resultado_pytest["compila"] and resultado_pytest["tests_passed"] > 0:
        print("[Estrategia 2] Corriendo mutmut (esto puede tardar)...")
        resultado_mutmut = correr_mutmut(destino_path)
    else:
        print("[Estrategia 2] Los tests no compilan tras los intentos; se omite mutmut.")

    reporte = {
        "estrategia": "2_iterativo",
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
        carpeta_salida="resultados/api-tareas_estrategia2",
    )

    reporte_limpio = json.loads(json.dumps(reporte, default=str))
    if reporte_limpio.get("pytest", {}).get("salida_cruda"):
        del reporte_limpio["pytest"]["salida_cruda"]

    print("\n=== REPORTE ===")
    print(json.dumps(reporte_limpio, indent=2, ensure_ascii=False))

    Path("resultados").mkdir(exist_ok=True)
    with open("resultados/reporte_estrategia2.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False, default=str)
