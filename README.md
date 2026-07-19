# Tesis - Mutation Testing con LLM

## Setup en Codespaces

```bash
pip install fastapi uvicorn "sqlalchemy>=2.0" pydantic pytest pytest-cov httpx mutmut google-genai
```

## Configurar API key de Gemini

Consigue tu key en https://aistudio.google.com/apikey y expórtala:

```bash
export GOOGLE_API_KEY="tu-api-key-aqui"
```

(Mejor aún: agrégala como Codespaces Secret en GitHub para que persista.)

## Correr la Estrategia 1 (prompting tradicional)

```bash
cd tesis-mutation-testing
python estrategias/estrategia_1_prompt_simple.py
```

Esto:
1. Lee `sujetos/api-tareas/services.py`
2. Le pide a Gemini 2.5 Flash que genere tests
3. Copia el proyecto a `resultados/api-tareas_estrategia1/`
4. Corre pytest y mutmut sobre los tests generados
5. Guarda el reporte completo en `resultados/reporte_estrategia1.json`

## Estructura

```
tesis-mutation-testing/
├── sujetos/
│   └── api-tareas/          # proyecto sujeto (ya con baseline validado: 88.6%)
├── shared/
│   ├── llm_client.py        # llamadas a Gemini
│   └── metricas.py          # ejecucion de pytest/mutmut y parseo de resultados
├── estrategias/
│   └── estrategia_1_prompt_simple.py
└── resultados/               # aqui se guardan los reportes JSON
```

## Proximos pasos

- Estrategia 2 (ciclo iterativo de correccion)
- Estrategia 3 (retroalimentacion de mutation testing)
- Repetir sobre mas archivos fuente (routes.py, schemas.py)
- Repetir sobre mas proyectos sujeto
