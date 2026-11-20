import os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

HORAS_POR_DEDICACION = {
    "Simple": 10,
    "Semi-exclusiva": 20,
    "Exclusiva": 40,
}

COSTO_MENSUAL_POR_DEDICACION = {
    "Simple": float(os.getenv("COSTO_SIMPLE", "450000")),
    "Semi-exclusiva": float(os.getenv("COSTO_SEMI", "900000")),
    "Exclusiva": float(os.getenv("COSTO_EXCLUSIVA", "1800000")),
}

UMBRAL_ALERTA_SIMPLE_PCT = float(os.getenv("UMBRAL_ALERTA_SIMPLE_PCT", "50"))

UMBRAL_COMPATIBILIDAD = int(os.getenv("UMBRAL_COMPATIBILIDAD", "25"))
