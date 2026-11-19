"""
API del Sistema Inteligente de Gestión de Planta Docente.

Ejecutar desde la raíz del proyecto:
    uvicorn backend.main:app --reload
Documentación interactiva: http://127.0.0.1:8000/docs
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import database as db
from backend import ia
from backend.errores import registrar_manejadores
from backend.routers import docentes, ia as ia_router, planta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()          # crea tablas y carga datos de ejemplo si la base está vacía
    yield


app = FastAPI(
    title="API Sistema de Gestión de Planta Docente",
    version="2.0",
    description="Gestión de docentes, materias, indicadores, alertas y análisis de CV con IA (Ollama).",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
registrar_manejadores(app)

app.include_router(docentes.router)
app.include_router(planta.router)
app.include_router(ia_router.router)


@app.get("/", tags=["Estado"], summary="Estado de la API")
def home():
    return {"mensaje": "API de Planta Docente funcionando correctamente", "docs": "/docs"}


@app.get("/health", tags=["Estado"], summary="Estado de la base de datos y de la IA")
def health():
    try:
        total = db.calcular_indicadores()["total_docentes"]
        estado_db = {"base_de_datos": "ok", "docentes": total}
    except Exception as e:  # noqa: BLE001
        estado_db = {"base_de_datos": f"error: {e}"}
    return {**estado_db, **ia.estado()}
