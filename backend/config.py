"""
Configuración central del backend.

Todos los valores se pueden sobrescribir con variables de entorno, así el mismo
código funciona corriendo local (python/uvicorn) o dentro de Docker.
"""
import os

# --- Inteligencia Artificial (Ollama local, gratuito) ---
# Local:  http://localhost:11434
# Docker: http://host.docker.internal:11434  (Ollama corre en la PC, fuera del contenedor)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # segundos

# --- Reglas de negocio de la planta docente ---
# Horas semanales que representa cada dedicación (régimen universitario de referencia).
HORAS_POR_DEDICACION = {
    "Simple": 10,
    "Semi-exclusiva": 20,
    "Exclusiva": 40,
}

# Costo mensual de referencia por dedicación (valores FICTICIOS para la demo,
# se pueden ajustar por variable de entorno sin tocar código).
COSTO_MENSUAL_POR_DEDICACION = {
    "Simple": float(os.getenv("COSTO_SIMPLE", "450000")),
    "Semi-exclusiva": float(os.getenv("COSTO_SEMI", "900000")),
    "Exclusiva": float(os.getenv("COSTO_EXCLUSIVA", "1800000")),
}

# Si más de este porcentaje de la planta tiene dedicación Simple, se genera una alerta.
UMBRAL_ALERTA_SIMPLE_PCT = float(os.getenv("UMBRAL_ALERTA_SIMPLE_PCT", "50"))

# Puntaje mínimo (0-100) para considerar que un CV es compatible con una materia.
UMBRAL_COMPATIBILIDAD = int(os.getenv("UMBRAL_COMPATIBILIDAD", "25"))
