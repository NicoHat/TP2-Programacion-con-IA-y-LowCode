from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Response, status

from backend import database as db
from backend.schemas import Dedicacion, Docente, DocenteActualizar, DocenteCrear, Evaluacion

router = APIRouter(prefix="/docentes", tags=["Docentes"])


def _buscar_o_404(docente_id: int) -> dict:
    docente = db.obtener_docente_por_id(docente_id)
    if not docente:
        raise HTTPException(status_code=404, detail=f"No existe un docente con ID {docente_id}.")
    return docente


@router.get("", response_model=list[Docente], summary="Listar, buscar y filtrar docentes")
def listar_docentes(
    materia: Optional[str] = Query(None, description="Filtra por materia (búsqueda parcial)"),
    dedicacion: Optional[Dedicacion] = Query(None, description="Filtra por dedicación exacta"),
    busqueda: Optional[str] = Query(None, description="Texto libre en nombre, email o CV"),
):
    return db.obtener_docentes(materia=materia, dedicacion=dedicacion, busqueda=busqueda)


@router.get("/{docente_id}", response_model=Docente, summary="Obtener un docente por ID")
def obtener_docente(docente_id: int):
    return _buscar_o_404(docente_id)


@router.post("", response_model=Docente, status_code=status.HTTP_201_CREATED,
             summary="Registrar un docente")
def crear_docente(datos: DocenteCrear):
    nuevo_id = db.crear_nuevo_docente(**datos.model_dump())
    return db.obtener_docente_por_id(nuevo_id)


@router.patch("/{docente_id}", response_model=Docente, summary="Modificar datos de un docente")
@router.put("/{docente_id}", response_model=Docente, include_in_schema=False)
def actualizar_docente(docente_id: int, cambios: DocenteActualizar):
    _buscar_o_404(docente_id)
    db.actualizar_docente(docente_id, **cambios.model_dump(exclude_none=True))
    return db.obtener_docente_por_id(docente_id)


@router.delete("/{docente_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Dar de baja un docente")
def eliminar_docente(docente_id: int):
    if not db.eliminar_docente(docente_id):
        raise HTTPException(status_code=404, detail=f"No existe un docente con ID {docente_id}.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{docente_id}/evaluaciones", response_model=list[Evaluacion],
            summary="Historial de análisis de CV de un docente")
def evaluaciones_docente(docente_id: int):
    _buscar_o_404(docente_id)
    return db.obtener_historial_evaluaciones(docente_id)
