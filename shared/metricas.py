"""
Funciones para ejecutar pytest y mutmut sobre un proyecto copiado,
y extraer las metricas que necesita el articulo.
"""
import re
import shutil
import subprocess
import time
from pathlib import Path


def preparar_copia_proyecto(sujeto_dir: Path, destino_dir: Path) -> None:
    """Copia el proyecto sujeto a una carpeta limpia para esta estrategia."""
    if destino_dir.exists():
        shutil.rmtree(destino_dir)
    shutil.copytree(
        sujeto_dir,
        destino_dir,
        ignore=shutil.ignore_patterns(
            "venv", "__pycache__", ".pytest_cache", ".mutmut-cache",
            "mutants", "*.db", ".git"
        ),
    )


def reemplazar_tests(destino_dir: Path, codigo_test: str, nombre_archivo: str = "test_generado.py") -> Path:
    """Borra los tests existentes y deja solo el generado por el LLM."""
    tests_dir = destino_dir / "tests"
    if tests_dir.exists():
        for archivo in tests_dir.glob("test_*.py"):
            archivo.unlink()
    else:
        tests_dir.mkdir()

    ruta_test = tests_dir / nombre_archivo
    ruta_test.write_text(codigo_test, encoding="utf-8")

    conftest = tests_dir / "conftest.py"
    conftest_original = destino_dir / "tests_conftest_backup.py"
    if conftest_original.exists() and not conftest.exists():
        shutil.copy(conftest_original, conftest)

    return ruta_test


def correr_pytest(proyecto_dir: Path, python_bin: str = "python") -> dict:
    """
    Corre pytest en el proyecto copiado.
    Retorna si compilo, cuantos pasaron/fallaron, y el tiempo.
    """
    inicio = time.perf_counter()
    resultado = subprocess.run(
        [python_bin, "-m", "pytest", "-v", "--tb=short"],
        cwd=proyecto_dir,
        capture_output=True,
        text=True,
        timeout=120,
    )
    tiempo = round(time.perf_counter() - inicio, 3)

    salida = resultado.stdout + resultado.stderr

    compila = "SyntaxError" not in salida and "collected 0 items" not in salida
    hubo_error_coleccion = "ERROR collecting" in salida or "ImportError" in salida

    m_passed = re.search(r"(\d+) passed", salida)
    m_failed = re.search(r"(\d+) failed", salida)
    m_error = re.search(r"(\d+) error", salida)

    return {
        "compila": compila and not hubo_error_coleccion,
        "tests_passed": int(m_passed.group(1)) if m_passed else 0,
        "tests_failed": int(m_failed.group(1)) if m_failed else 0,
        "tests_error": int(m_error.group(1)) if m_error else 0,
        "tiempo_segundos": tiempo,
        "salida_cruda": salida[-3000:],
    }


def correr_mutmut(proyecto_dir: Path, python_bin: str = "python", timeout: int = 600) -> dict:
    """
    Corre mutmut run + mutmut results sobre el proyecto copiado.
    Cuenta killed/survived/timeout/suspicious/no-tests linea por linea
    (mas confiable que parsear la linea resumen con emojis).
    """
    cache = proyecto_dir / ".mutmut-cache"
    if cache.exists():
        cache.unlink()
    mutants_dir = proyecto_dir / "mutants"
    if mutants_dir.exists():
        shutil.rmtree(mutants_dir)

    inicio = time.perf_counter()
    subprocess.run(
        [python_bin, "-m", "mutmut", "run"],
        cwd=proyecto_dir,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    tiempo = round(time.perf_counter() - inicio, 3)

    resultado_results = subprocess.run(
        [python_bin, "-m", "mutmut", "results", "--all", "true"],
        cwd=proyecto_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    salida_results = resultado_results.stdout

    lineas_mutantes = [
        linea.strip() for linea in salida_results.splitlines()
        if ": " in linea
        and not linea.strip().startswith(("mutmut", "UserWarning", "warnings.warn"))
        and linea.strip().startswith("services.")
    ]

    killed = sum(1 for l in lineas_mutantes if l.endswith(": killed"))
    survived = sum(1 for l in lineas_mutantes if l.endswith(": survived"))
    timeouts = sum(1 for l in lineas_mutantes if l.endswith(": timeout"))
    suspicious = sum(1 for l in lineas_mutantes if l.endswith(": suspicious"))
    no_cubiertos = sum(1 for l in lineas_mutantes if l.endswith(": no tests"))
    total = len(lineas_mutantes)

    mutation_score = round(killed / (killed + survived) * 100, 2) if (killed + survived) > 0 else 0.0

    return {
        "mutantes_totales": total,
        "killed": killed,
        "survived": survived,
        "sin_cobertura": no_cubiertos,
        "timeouts": timeouts,
        "suspicious": suspicious,
        "mutation_score": mutation_score,
        "tiempo_segundos": tiempo,
        "detalle_survived": [
            linea.strip() for linea in salida_results.splitlines() if ": survived" in linea
        ],
    }


def obtener_diff_mutante(proyecto_dir: Path, nombre_mutante: str, python_bin: str = "python") -> str:
    """
    Obtiene el diff exacto de un mutante especifico usando 'mutmut show'.
    nombre_mutante es el identificador que aparece en 'mutmut results',
    ej: 'services.x_crear_tarea__mutmut_5'
    """
    import re as _re

    resultado = subprocess.run(
        [python_bin, "-m", "mutmut", "show", nombre_mutante],
        cwd=proyecto_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    salida = resultado.stdout + resultado.stderr
    # limpia posibles codigos de color ANSI
    salida_limpia = _re.sub(r"\x1b\[[0-9;]*m", "", salida)
    return salida_limpia.strip()
