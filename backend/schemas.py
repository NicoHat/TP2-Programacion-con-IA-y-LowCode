from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Dedicacion = Literal["Simple", "Semi-exclusiva", "Exclusiva"]

PATRON_EMAIL = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class DocenteCrear(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=120, examples=["Ing. Ana López"])
    email: str = Field(..., pattern=PATRON_EMAIL, max_length=120, examples=["alopez@universidad.edu.ar"])
    materia: str = Field(..., min_length=2, max_length=120, examples=["Bases de Datos Relacionales"])
    dedicacion: Dedicacion = Field(..., examples=["Semi-exclusiva"])
    cv_resumen: str = Field("", max_length=5000)


class DocenteActualizar(BaseModel):
    nombre: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[str] = Field(None, pattern=PATRON_EMAIL, max_length=120)
    materia: Optional[str] = Field(None, min_length=2, max_length=120)
    dedicacion: Optional[Dedicacion] = None
    cv_resumen: Optional[str] = Field(None, max_length=5000)

    @model_validator(mode="after")
    def al_menos_un_campo(self):
        if all(v is None for v in self.model_dump().values()):
            raise ValueError("Debe enviar al menos un campo para actualizar.")
        return self


class Docente(BaseModel):
    id: int
    nombre: str
    email: str
    materia: str
    materia_id: Optional[int] = None
    dedicacion: str
    cv_resumen: Optional[str] = ""
    fecha_alta: Optional[str] = None


class Materia(BaseModel):
    id: int
    nombre: str
    departamento: str
    cuatrimestre: str
    horas_semanales: int
    cantidad_docentes: int
    cubierta: bool


class AnalisisCVEntrada(BaseModel):
    cv_texto: str = Field(..., min_length=20, max_length=20000,
                          description="Texto del currículum o perfil a analizar.")
    docente_id: Optional[int] = Field(None, gt=0,
                                      description="Opcional: docente al que pertenece el CV.")


class AnalisisIA(BaseModel):
    resumen: str = Field(..., min_length=10)
    areas_experiencia: list[str] = []
    titulos: list[str] = []
    anios_experiencia: Optional[int] = Field(None, ge=0, le=70)
    materias_sugeridas: list[str] = []


class CompatibilidadMateria(BaseModel):
    materia: str
    puntaje: int = Field(..., ge=0, le=100)
    coincidencias: list[str]


class AnalisisCVRespuesta(BaseModel):
    origen_ia: AnalisisIA
    compatibilidad_reglas: list[CompatibilidadMateria]
    advertencias: list[str]
    modelo: str
    docente_id: Optional[int] = None
    requiere_revision_humana: bool = True


class EvaluacionConfirmar(BaseModel):
    cv_texto: str = Field(..., min_length=30, max_length=20000)
    resumen_aprobado: str = Field(..., min_length=10, max_length=5000)
    docente_id: Optional[int] = Field(None, gt=0)


class Evaluacion(BaseModel):
    id: int
    docente_id: Optional[int] = None
    docente_nombre: Optional[str] = None
    materia: Optional[str] = None
    cv_texto_original: str
    resumen_ia: str
    fecha_evaluacion: Optional[str] = None


class ReporteIA(BaseModel):
    reporte: str
    modelo: str
    indicadores: dict
    alertas: list[dict]
