"""
Estrategia 3: Retroalimentacion de mutation testing.
Genera tests (con correccion iterativa como la Estrategia 2), corre mutmut,
y si hay mutantes supervivientes, le muestra el diff exacto al LLM para
que mejore los tests y los detecte. Repite hasta un maximo de ciclos.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.llm_client import generar_texto, extraer_codigo_python
from shared.metricas import (
    preparar_copia_proyecto,
    reemplazar_tests,
    correr_pytest,
    correr_mutmut,
    obtener_diff_mutante,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from estrategia_2_iterativo import generar_tests_estrategia_2  # reutiliza la generacion + correccion


PROMPT_MUTATION_FEEDBACK = """Tienes un archivo de tests en pytest que ya pasa correctamente,
pero mutation testing (mutmut) encontro cambios en el codigo original que
tus tests NO detectan (mutantes que sobreviven). Esto significa que hay
defectos que estos tests no pueden detectar.

Codigo de test actual (COMPLETO, no lo resumas):
CODIGO_TEST_AQUI
{codigo_test}
FIN_CODIGO_TEST

A continuacion los cambios especificos (mutantes) que NO fueron detectados.
Cada uno es un diff mostrando la version original vs la mutada:

MUTANTES_NO_DETECTADOS_AQUI
{mutantes_sobrevivientes}
FIN_MUTANTES_NO_DETECTADOS

Tu tarea:
- Modifica o agrega pruebas para que detecten estos cambios especificos
  (es decir, que fallen si el codigo tuviera ese defecto).
- Mantén todas las pruebas existentes que ya funcionan, no las elimines.
- NUNCA redefinas, copies, reimplementes, ni hagas monkeypatching de
  sys.modules para el codigo fuente, los modelos SQLAlchemy, ni los
  schemas Pydantic. Sigue importando todo directamente del modulo real.
- Evita el uso de mocks/monkeypatch sobre metodos internos de SQLAlchemy
  (como Session.query o Session.filter) salvo que sea estrictamente
  necesario; prefiere pruebas que usen la base de datos real en memoria
  y verifiquen el comportamiento observable de la funcion.
- Responde SOLO con el archivo de test COMPLETO y actualizado, sin
  explicaciones fuera del codigo.
"""

MAX_CICLOS_FEEDBACK = 3
MAX_MUTANTES_POR_CICLO = 5  # limitar para no saturar el prompt


def ejecutar(sujeto_dir: str, archivo_fuente: str, carpeta_salida: str):
    sujeto_path = Path(sujeto_dir)
    destino_path = Path(carpeta_salida)

    codigo_fuente = (sujeto_path / archivo_fuente).read_text(encoding="utf-8")

    print(f"[Estrategia 3] Generando tests iniciales para {archivo_fuente}...")
    resultado_generacion = generar_tests_estrategia_2(
        codigo_fuente, archivo_fuente, sujeto_path, destino_path
    )
    codigo_test = resultado_generacion["codigo_test"]
    resultado_pytest = resultado_generacion.pop("resultado_pytest_final")

    tiempo_total = resultado_generacion["tiempo_generacion_segundos"]
    tokens_entrada_total = resultado_generacion["tokens_entrada"]
    tokens_salida_total = resultado_generacion["tokens_salida"]

    historial_ciclos = []
    resultado_mutmut = None

    if not (resultado_pytest["compila"] and resultado_pytest["tests_passed"] > 0):
        print("[Estrategia 3] Los tests iniciales no compilan; se omite el ciclo de feedback.")
    else:
        for ciclo in range(1, MAX_CICLOS_FEEDBACK + 1):
            print(f"[Estrategia 3] Ciclo {ciclo}: corriendo mutmut...")
            resultado_mutmut = correr_mutmut(destino_path)

            supervivientes = resultado_mutmut["detalle_survived"]
            historial_ciclos.append({
                "ciclo": ciclo,
                "mutation_score": resultado_mutmut["mutation_score"],
                "survived": resultado_mutmut["survived"],
            })

            if not supervivientes:
                print(f"[Estrategia 3] Ciclo {ciclo}: 0 mutantes sobrevivientes, no hace falta mas feedback.")
                break

            if ciclo == MAX_CICLOS_FEEDBACK:
                print(f"[Estrategia 3] Se alcanzo el maximo de {MAX_CICLOS_FEEDBACK} ciclos.")
                break

            nombres_mutantes = [linea.split(":")[0].strip() for linea in supervivientes][:MAX_MUTANTES_POR_CICLO]

            print(f"[Estrategia 3] Ciclo {ciclo}: obteniendo diffs de {len(nombres_mutantes)} mutantes sobrevivientes...")
            diffs = []
            for nombre in nombres_mutantes:
                diff = obtener_diff_mutante(destino_path, nombre)
                diffs.append(f"--- Mutante: {nombre} ---\n{diff}")
            texto_mutantes = "\n\n".join(diffs)

            prompt_feedback = PROMPT_MUTATION_FEEDBACK.format(
                codigo_test=codigo_test,
                mutantes_sobrevivientes=texto_mutantes,
            )

            print(f"[Estrategia 3] Ciclo {ciclo}: pidiendo al LLM que mejore los tests...")
            resultado_llm = generar_texto(prompt_feedback)
            codigo_test = extraer_codigo_python(resultado_llm["texto"])
            tiempo_total += resultado_llm["tiempo_segundos"]
            tokens_entrada_total += resultado_llm["tokens_entrada"]
            tokens_salida_total += resultado_llm["tokens_salida"]

            preparar_copia_proyecto(sujeto_path, destino_path)
            reemplazar_tests(destino_path, codigo_test)
            resultado_pytest = correr_pytest(destino_path)

            if not (resultado_pytest["compila"] and resultado_pytest["tests_passed"] > 0 and resultado_pytest["tests_failed"] == 0 and resultado_pytest["tests_error"] == 0):
                print(f"[Estrategia 3] Ciclo {ciclo}: los tests mejorados no compilan/pasan/tienen fallos, se detiene el ciclo.")
                break

    reporte = {
        "estrategia": "3_mutation_feedback",
        "archivo_fuente": archivo_fuente,
        "generacion": {
            "codigo_test": codigo_test,
            "intentos_usados_generacion_inicial": resultado_generacion["intentos_usados"],
            "ciclos_feedback_usados": len(historial_ciclos),
            "historial_ciclos": historial_ciclos,
            "tiempo_generacion_segundos": round(tiempo_total, 3),
            "tokens_entrada": tokens_entrada_total,
            "tokens_salida": tokens_salida_total,
        },
        "pytest": resultado_pytest,
        "mutmut_final": resultado_mutmut,
    }
    return reporte


if __name__ == "__main__":
    import json

    reporte = ejecutar(
        sujeto_dir="sujetos/api-tareas",
        archivo_fuente="services.py",
        carpeta_salida="resultados/api-tareas_estrategia3",
    )

    reporte_limpio = json.loads(json.dumps(reporte, default=str))
    if reporte_limpio.get("pytest", {}).get("salida_cruda"):
        del reporte_limpio["pytest"]["salida_cruda"]

    print("\n=== REPORTE ===")
    print(json.dumps(reporte_limpio, indent=2, ensure_ascii=False))

    Path("resultados").mkdir(exist_ok=True)
    with open("resultados/reporte_estrategia3.json", "w", encoding="utf-8") as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False, default=str)
