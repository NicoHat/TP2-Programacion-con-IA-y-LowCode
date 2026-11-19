"""
Reglas de negocio calculadas con Python (SIN inteligencia artificial).

La consigna pide distinguir lo que se calcula con reglas explícitas de lo que
genera la IA. Todo lo de este módulo es determinístico: mismos datos -> mismo
resultado, y cada número se puede explicar.
"""
import re
import unicodedata

from backend import database as db
from backend.config import (
    COSTO_MENSUAL_POR_DEDICACION,
    HORAS_POR_DEDICACION,
    UMBRAL_ALERTA_SIMPLE_PCT,
    UMBRAL_COMPATIBILIDAD,
)

# Palabras que no aportan para comparar un CV con una materia.
STOPWORDS = {
    "de", "del", "la", "las", "el", "los", "y", "e", "en", "a", "con", "para",
    "por", "i", "ii", "iii", "general", "departamento", "elementos", "introduccion",
}

# Siglas cortas que sí son significativas aunque tengan 2 letras.
SIGLAS = {"ia", "ai", "bd", "ml"}

# Palabras clave extra por tema: si la materia contiene la clave,
# también se buscan estos términos en el CV.
SINONIMOS = {
    "datos": ["sql", "sqlite", "postgresql", "mysql", "etl", "modelado"],
    "relacional": ["sql", "integridad referencial", "normalizacion", "modelado relacional"],
    "programacion": ["python", "java", "c++", "javascript", "codigo"],
    "inteligencia": ["machine learning", "ia", "llm", "llms", "nlp", "ollama", "redes neuronales"],
    "ia": ["machine learning", "llm", "llms", "nlp", "ollama", "inteligencia artificial"],
    "lowcode": ["n8n", "streamlit", "low-code", "automatizacion"],
    "software": ["api", "fastapi", "scrum", "agil", "microservicios", "testing"],
    "algoritmos": ["grafos", "complejidad", "estructuras"],
    "matematica": ["algebra", "logica", "combinatoria", "conjuntos"],
    "redes": ["tcp/ip", "linux", "docker", "servidores", "seguridad"],
    "arquitectura": ["hardware", "procesadores", "linux"],
}


# ------------------------------------------------------------- utilidades
def normalizar(texto: str) -> str:
    """minúsculas y sin tildes: 'Programación' -> 'programacion'."""
    texto = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return texto.lower()


def palabras_clave(texto: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9+#/]+", normalizar(texto))
    return {t for t in tokens if (len(t) > 2 or t in SIGLAS) and t not in STOPWORDS}


# ------------------------------------------------------------- materias
def materias_con_cobertura() -> list[dict]:
    """Cada materia del catálogo + cuántos docentes tiene asignados."""
    materias = db.listar_materias()
    por_materia = db.calcular_indicadores()["por_materia"]
    conteo = {normalizar(k): v for k, v in por_materia.items()}
    resultado = []
    for m in materias:
        cantidad = conteo.get(normalizar(m["nombre"]), 0)
        resultado.append({**m, "cantidad_docentes": cantidad, "cubierta": cantidad > 0})
    return resultado


# ------------------------------------------------------------- indicadores
def indicadores_planta() -> dict:
    """Indicadores completos de la planta docente."""
    base = db.calcular_indicadores()
    docentes = db.obtener_docentes()
    materias = materias_con_cobertura()

    total = base["total_docentes"]
    por_dedicacion = base["por_dedicacion"]

    porcentaje_dedicacion = {
        ded: round(cant * 100 / total, 1) if total else 0.0
        for ded, cant in por_dedicacion.items()
    }
    horas_contratadas = sum(HORAS_POR_DEDICACION.get(d["dedicacion"], 0) for d in docentes)
    costo_mensual = sum(COSTO_MENSUAL_POR_DEDICACION.get(d["dedicacion"], 0) for d in docentes)
    horas_catedra = sum(m["horas_semanales"] for m in materias)

    sin_cobertura = [m["nombre"] for m in materias if not m["cubierta"]]
    un_solo_docente = [m["nombre"] for m in materias if m["cantidad_docentes"] == 1]
    sin_cv = [d["nombre"] for d in docentes if not (d.get("cv_resumen") or "").strip()]

    return {
        "total_docentes": total,
        "total_materias": len(materias),
        "distribucion": base["distribucion"],
        "por_dedicacion": por_dedicacion,
        "porcentaje_dedicacion": porcentaje_dedicacion,
        "por_materia": base["por_materia"],
        "horas_semanales_contratadas": horas_contratadas,
        "horas_semanales_catedra": horas_catedra,
        "promedio_docentes_por_materia": round(total / len(materias), 2) if materias else 0.0,
        "costo_mensual_estimado": costo_mensual,
        "materias_sin_cobertura": sin_cobertura,
        "materias_con_un_solo_docente": un_solo_docente,
        "docentes_sin_cv": sin_cv,
        "cobertura_pct": round((len(materias) - len(sin_cobertura)) * 100 / len(materias), 1) if materias else 0.0,
    }


def generar_alertas(indicadores: dict | None = None) -> dict:
    """
    Genera alertas a partir de los indicadores.
    Pensado para el workflow de notificación de n8n: el nodo IF puede decidir
    con el campo 'hay_alertas_altas'.
    """
    ind = indicadores or indicadores_planta()
    alertas = []

    for materia in ind["materias_sin_cobertura"]:
        alertas.append({
            "tipo": "materia_sin_cobertura", "severidad": "alta", "referencia": materia,
            "mensaje": f"La materia '{materia}' no tiene ningún docente asignado.",
        })
    for materia in ind["materias_con_un_solo_docente"]:
        alertas.append({
            "tipo": "cobertura_minima", "severidad": "media", "referencia": materia,
            "mensaje": f"La materia '{materia}' depende de un único docente.",
        })
    pct_simple = ind["porcentaje_dedicacion"].get("Simple", 0)
    if ind["total_docentes"] and pct_simple > UMBRAL_ALERTA_SIMPLE_PCT:
        alertas.append({
            "tipo": "exceso_dedicacion_simple", "severidad": "media", "referencia": f"{pct_simple}%",
            "mensaje": f"El {pct_simple}% de la planta tiene dedicación Simple "
                       f"(umbral {UMBRAL_ALERTA_SIMPLE_PCT}%).",
        })
    for nombre in ind["docentes_sin_cv"]:
        alertas.append({
            "tipo": "docente_sin_cv", "severidad": "baja", "referencia": nombre,
            "mensaje": f"El docente '{nombre}' no tiene CV ni perfil cargado.",
        })

    return {
        "total": len(alertas),
        "hay_alertas_altas": any(a["severidad"] == "alta" for a in alertas),
        "por_severidad": {s: sum(a["severidad"] == s for a in alertas) for s in ("alta", "media", "baja")},
        "alertas": alertas,
    }


# ------------------------------------------------------------- compatibilidad CV-materia
def compatibilidad_cv_materias(cv_texto: str, limite: int = 5) -> list[dict]:
    """
    Scoring por reglas explícitas:
      - Cada palabra significativa del NOMBRE de la materia es un
        "concepto". Un concepto se cumple si en el CV aparece la palabra o
        alguno de sus sinónimos (SINONIMOS).
      - puntaje = conceptos cumplidos / conceptos totales * 100
    """
    cv_norm = normalizar(cv_texto)
    cv_tokens = palabras_clave(cv_texto)

    def aparece(termino: str) -> bool:
        return termino in cv_tokens or (" " in termino or "-" in termino) and termino in cv_norm

    resultados = []
    for m in db.listar_materias():
        conceptos = palabras_clave(m["nombre"])
        if not conceptos:
            continue
        coincidencias, cumplidos = set(), 0
        for concepto in conceptos:
            grupo = {concepto}
            for clave, extras in SINONIMOS.items():
                # claves cortas (ej. "ia") deben coincidir exacto: evita que "ingenierIA" matchee
                if clave == concepto or (len(clave) > 3 and clave in concepto):
                    grupo.update(extras)
            encontrados = {t for t in grupo if aparece(t)}
            if encontrados:
                cumplidos += 1
                coincidencias |= encontrados
        coincidencias = sorted(coincidencias)
        puntaje = round(cumplidos * 100 / len(conceptos))
        if puntaje >= UMBRAL_COMPATIBILIDAD:
            resultados.append({"materia": m["nombre"], "puntaje": min(puntaje, 100),
                               "coincidencias": coincidencias})

    resultados.sort(key=lambda r: r["puntaje"], reverse=True)
    return resultados[:limite]
