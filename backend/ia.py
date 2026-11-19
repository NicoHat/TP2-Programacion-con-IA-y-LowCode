"""
Integración con IA mediante Ollama (modelos locales, gratuitos, sin enviar datos
personales a servicios externos).

Por qué Ollama + llama3:
  - Cumple la consigna: gratis y se ejecuta localmente.
  - Los CVs tienen datos personales: no salen de la máquina.
Límites conocidos (hay que explicarlos en la defensa):
  - Puede inventar datos ("alucinar") -> validamos la estructura y contrastamos
    las materias sugeridas contra el catálogo real.
  - Es lento en PCs sin GPU -> timeout configurable (OLLAMA_TIMEOUT).
  - La IA nunca guarda nada sola: una persona aprueba (ver POST /evaluaciones).
"""
import json

import requests
from pydantic import ValidationError

from backend.config import OLLAMA_MODEL, OLLAMA_TIMEOUT, OLLAMA_URL
from backend.reglas import normalizar
from backend.schemas import AnalisisIA


class IAError(Exception):
    """Error de la capa de IA con el código HTTP que debe devolver la API."""
    def __init__(self, mensaje: str, status_code: int = 502):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.status_code = status_code


# ------------------------------------------------------------- cliente Ollama
def _generar(prompt: str, formato_json: bool = False) -> str:
    payload = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False,
               "options": {"temperature": 0.2}}
    if formato_json:
        payload["format"] = "json"   # Ollama fuerza la salida a JSON válido
    try:
        r = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=OLLAMA_TIMEOUT)
    except requests.exceptions.ConnectionError:
        raise IAError(f"No se pudo conectar con Ollama en {OLLAMA_URL}. "
                      "Verificá que Ollama esté abierto ('ollama serve').", 503)
    except requests.exceptions.Timeout:
        raise IAError(f"Ollama tardó más de {OLLAMA_TIMEOUT}s en responder.", 504)

    if r.status_code == 404:
        raise IAError(f"El modelo '{OLLAMA_MODEL}' no está descargado. "
                      f"Ejecutá: ollama pull {OLLAMA_MODEL}", 503)
    if r.status_code != 200:
        raise IAError(f"Ollama respondió con error {r.status_code}: {r.text[:200]}", 502)

    texto = (r.json().get("response") or "").strip()
    if not texto:
        raise IAError("La IA devolvió una respuesta vacía.", 502)
    return texto


def estado() -> dict:
    """Chequea si Ollama está disponible y si el modelo configurado está descargado."""
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        modelos = [m.get("name", "") for m in r.json().get("models", [])]
        disponible = any(m.split(":")[0] == OLLAMA_MODEL.split(":")[0] for m in modelos)
        return {"ollama": "ok", "modelo": OLLAMA_MODEL, "modelo_descargado": disponible}
    except Exception:
        return {"ollama": "no disponible", "modelo": OLLAMA_MODEL, "modelo_descargado": False}


# ------------------------------------------------------------- análisis de CV
PROMPT_CV = """Sos un asistente de Recursos Humanos de una universidad.
Analizá el siguiente currículum de un docente y respondé SOLO con un JSON con esta forma exacta:
{{
  "resumen": "resumen del perfil en 2 o 3 oraciones, en español",
  "areas_experiencia": ["area 1", "area 2"],
  "titulos": ["titulo 1"],
  "anios_experiencia": 0,
  "materias_sugeridas": ["nombre exacto de materia"]
}}
Reglas:
- Usá solo información presente en el CV. Si un dato no aparece, usá [] o null.
- En "materias_sugeridas" elegí SOLO nombres de esta lista: {materias}

Currículum:
\"\"\"{cv}\"\"\"
"""


def _parsear_analisis(texto: str) -> AnalisisIA:
    try:
        datos = json.loads(texto)
    except json.JSONDecodeError:
        # A veces el modelo agrega texto antes/después del JSON: lo recortamos.
        inicio, fin = texto.find("{"), texto.rfind("}")
        if inicio == -1 or fin <= inicio:
            raise ValueError("La respuesta no contiene JSON.")
        datos = json.loads(texto[inicio:fin + 1])
    if isinstance(datos.get("anios_experiencia"), str):
        digitos = "".join(c for c in datos["anios_experiencia"] if c.isdigit())
        datos["anios_experiencia"] = int(digitos) if digitos else None
    return AnalisisIA(**datos)


def analizar_cv(cv_texto: str, materias_catalogo: list[str]) -> tuple[AnalisisIA, list[str]]:
    """
    Devuelve (analisis, advertencias).
    Valida la salida de la IA: estructura (Pydantic) + materias contra el catálogo.
    Reintenta una vez si la IA devuelve un JSON mal formado.
    """
    prompt = PROMPT_CV.format(materias=", ".join(materias_catalogo) or "(sin materias)",
                              cv=cv_texto[:8000])
    ultimo_error = None
    for _ in range(2):
        try:
            analisis = _parsear_analisis(_generar(prompt, formato_json=True))
            break
        except (ValueError, ValidationError, TypeError, AttributeError) as e:
            ultimo_error = e
    else:
        raise IAError(f"La IA devolvió un formato inválido dos veces seguidas: {ultimo_error}", 502)

    # --- Validación de resultados: no confiamos ciegamente en la IA ---
    advertencias = []
    catalogo = {normalizar(m): m for m in materias_catalogo}
    validas, inventadas = [], []
    for sugerida in analisis.materias_sugeridas:
        real = catalogo.get(normalizar(sugerida))
        (validas if real else inventadas).append(real or sugerida)
    if inventadas:
        advertencias.append("La IA sugirió materias que no existen en el catálogo y se descartaron: "
                            + ", ".join(inventadas))
    analisis.materias_sugeridas = list(dict.fromkeys(validas))

    cv_norm = normalizar(cv_texto)
    for titulo in analisis.titulos:
        primera = normalizar(titulo).split()[0] if titulo.strip() else ""
        if primera and len(primera) > 3 and primera not in cv_norm:
            advertencias.append(f"El título '{titulo}' no aparece textual en el CV: verificar.")
    if analisis.anios_experiencia is None:
        advertencias.append("La IA no pudo determinar los años de experiencia.")

    return analisis, advertencias


# ------------------------------------------------------------- reporte
PROMPT_REPORTE = """Sos analista de Recursos Humanos de una universidad.
Con estos indicadores de la planta docente (calculados por el sistema, son exactos):
{indicadores}

Y estas alertas detectadas:
{alertas}

Escribí en español un informe ejecutivo breve (máximo 200 palabras) con:
1. Situación general de la planta.
2. Principales riesgos.
3. Dos o tres recomendaciones concretas.
No inventes números: usá solo los datos dados."""


def generar_reporte(indicadores: dict, alertas: list[dict]) -> str:
    return _generar(PROMPT_REPORTE.format(
        indicadores=json.dumps(indicadores, ensure_ascii=False, indent=2),
        alertas="\n".join(f"- [{a['severidad']}] {a['mensaje']}" for a in alertas) or "- Ninguna",
    ))
