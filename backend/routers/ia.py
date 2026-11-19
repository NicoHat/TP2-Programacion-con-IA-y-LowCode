"""
Endpoints de Inteligencia Artificial.

Flujo con supervisión humana:
  1. POST /ia/analizar-cv  -> la IA PROPONE un análisis (no se guarda nada).
  2. La persona revisa/edita el resumen en la interfaz.
  3. POST /evaluaciones    -> se guarda lo APROBADO por la persona.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status

from backend import database as db
from backend import ia, reglas
from backend.config import OLLAMA_MODEL
from backend.schemas import (
    AnalisisCVEntrada, AnalisisCVRespuesta, Evaluacion, EvaluacionConfirmar, ReporteIA,
)

router = APIRouter(tags=["Inteligencia Artificial"])


@router.post("/ia/analizar-cv", response_model=AnalisisCVRespuesta,
             summary="Analizar un CV con IA + compatibilidad por reglas")
def analizar_cv(entrada: AnalisisCVEntrada):
    if entrada.docente_id and not db.obtener_docente_por_id(entrada.docente_id):
        raise HTTPException(status_code=404, detail=f"No existe un docente con ID {entrada.docente_id}.")

    catalogo = [m["nombre"] for m in db.listar_materias()]
    analisis, advertencias = ia.analizar_cv(entrada.cv_texto, catalogo)

    return AnalisisCVRespuesta(
        origen_ia=analisis,
        compatibilidad_reglas=reglas.compatibilidad_cv_materias(entrada.cv_texto),
        advertencias=advertencias,
        modelo=OLLAMA_MODEL,
        docente_id=entrada.docente_id,
    )


@router.post("/evaluaciones", response_model=Evaluacion, status_code=status.HTTP_201_CREATED,
             summary="Guardar una evaluación de CV aprobada por una persona")
def confirmar_evaluacion(datos: EvaluacionConfirmar):
    evaluacion_id = db.registrar_evaluacion_cv(
        datos.cv_texto, datos.resumen_aprobado, docente_id=datos.docente_id
    )
    historial = db.obtener_historial_evaluaciones(datos.docente_id) if datos.docente_id \
        else db.obtener_historial_evaluaciones()
    return next(e for e in historial if e["id"] == evaluacion_id)


@router.get("/evaluaciones", response_model=list[Evaluacion], summary="Historial de evaluaciones de CV")
def listar_evaluaciones(docente_id: Optional[int] = Query(None, gt=0)):
    return db.obtener_historial_evaluaciones(docente_id)


@router.delete("/evaluaciones/{evaluacion_id}", summary="Eliminar una evaluación del historial")
def eliminar_evaluacion(evaluacion_id: int):
    if not db.eliminar_evaluacion(evaluacion_id):
        raise HTTPException(status_code=404, detail=f"No existe la evaluación #{evaluacion_id}.")
    return {"mensaje": "Evaluación eliminada con éxito"}


@router.post("/ia/reporte", response_model=ReporteIA,
             summary="Informe ejecutivo de la planta redactado por IA")
def reporte_ia():
    indicadores = reglas.indicadores_planta()
    alertas = reglas.generar_alertas(indicadores)["alertas"]
    texto = ia.generar_reporte(indicadores, alertas)
    return ReporteIA(reporte=texto, modelo=OLLAMA_MODEL, indicadores=indicadores, alertas=alertas)


# --- Endpoint que usa el frontend (frontend/app.py) ---
@router.post("/procesar-cv-ia", summary="Analizar CV y guardarlo en el historial (usado por el frontend)")
def procesar_cv_ia(entrada: AnalisisCVEntrada):
    """
    Analiza el CV con IA, lo guarda en el historial y devuelve un texto listo para mostrar.
    Si Ollama no está disponible, entra en MODO CONTINGENCIA: devuelve solo el análisis
    calculado con reglas (sin IA) y lo marca con es_simulado=True.
    """
    docente = db.obtener_docente_por_id(entrada.docente_id) if entrada.docente_id else None
    if entrada.docente_id and not docente:
        raise HTTPException(status_code=404, detail=f"No existe un docente con ID {entrada.docente_id}.")

    compatibilidad = reglas.compatibilidad_cv_materias(entrada.cv_texto)
    texto_reglas = ("**Compatibilidad con materias (calculada por reglas):** " + ", ".join(
        f"{c['materia']} {c['puntaje']}%" for c in compatibilidad)) if compatibilidad \
        else "**Compatibilidad con materias (reglas):** sin coincidencias suficientes con el catálogo."

    try:
        catalogo = [m["nombre"] for m in db.listar_materias()]
        a, advertencias = ia.analizar_cv(entrada.cv_texto, catalogo)
        lineas = [f"**Resumen (IA):** {a.resumen}"]
        if a.areas_experiencia:
            lineas.append("**Áreas de experiencia:** " + ", ".join(a.areas_experiencia))
        if a.titulos:
            lineas.append("**Títulos:** " + ", ".join(a.titulos))
        if a.anios_experiencia is not None:
            lineas.append(f"**Años de experiencia:** {a.anios_experiencia}")
        if a.materias_sugeridas:
            lineas.append("**Materias sugeridas (IA):** " + ", ".join(a.materias_sugeridas))
        lineas.append(texto_reglas)
        if advertencias:
            lineas.append("⚠️ **Validación:** " + " ".join(advertencias))
        es_simulado, detalle = False, {"origen_ia": a.model_dump(), "advertencias": advertencias}
    except ia.IAError as e:
        if e.status_code not in (503, 504):   # error de formato de la IA: se informa, no se simula
            raise
        lineas = [
            "**Modo contingencia:** la IA no está disponible, se muestra solo el análisis por reglas.",
            texto_reglas,
            f"_Motivo: {e.mensaje}_",
        ]
        es_simulado, detalle = True, {"motivo": e.mensaje}

    resumen = "\n\n".join(lineas)
    evaluacion_id = db.registrar_evaluacion_cv(entrada.cv_texto, resumen, docente_id=entrada.docente_id)
    if docente:
        # registrar_evaluacion_cv copia el texto completo al perfil del docente.
        # Dejamos en el perfil solo el resumen de la IA, o el perfil anterior si no hubo IA.
        perfil = (docente.get("cv_resumen") or "") if es_simulado else detalle["origen_ia"]["resumen"]
        db.actualizar_docente(docente["id"], cv_resumen=perfil)
    return {
        "resumen_procesado": resumen,
        "evaluacion_id": evaluacion_id,
        "es_simulado": es_simulado,
        "compatibilidad_reglas": compatibilidad,
        "detalle": detalle,
    }
