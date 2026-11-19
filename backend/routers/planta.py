"""Endpoints de análisis de la planta: materias, indicadores y alertas (reglas, sin IA)."""
from fastapi import APIRouter

from backend import reglas
from backend.schemas import Materia

router = APIRouter(tags=["Planta docente"])


@router.get("/materias", response_model=list[Materia], summary="Materias con su cobertura docente")
def listar_materias():
    return reglas.materias_con_cobertura()


@router.get("/indicadores", summary="Indicadores calculados de la planta docente")
def obtener_indicadores():
    return reglas.indicadores_planta()


@router.get("/alertas", summary="Alertas de cobertura y planta (para n8n)")
def obtener_alertas():
    return reglas.generar_alertas()
