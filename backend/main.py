from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import sqlite3
import requests
from backend.database import (
    init_db,
    get_connection,
    actualizar_docente,
    eliminar_docente,
    registrar_evaluacion_cv,
    obtener_historial_evaluaciones,
    eliminar_evaluacion
)

app = FastAPI(title="API Sistema de Gestión Docente", version="1.0")

# Inicializar la base de datos al arrancar
@app.on_event("startup")
def startup_event():
    init_db()

class Docente(BaseModel):
    nombre: str
    email: str
    materia: str
    dedicacion: str
    cv_resumen: str = ""

@app.get("/")
def home():
    return {"mensaje": "API de Planta Docente funcionando correctamente"}

# 1. Listar todos los docentes
@app.get("/docentes")
def listar_docentes():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM docentes")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

# 2. Registrar un nuevo docente
@app.post("/docentes")
def crear_docente(docente: Docente):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO docentes (nombre, email, materia, dedicacion, cv_resumen) VALUES (?, ?, ?, ?, ?)",
        (docente.nombre, docente.email, docente.materia, docente.dedicacion, docente.cv_resumen)
    )
    conn.commit()
    conn.close()
    return {"mensaje": "Docente registrado con éxito"}

# 3. Consultar docente específico por ID
@app.get("/docentes/{docente_id}")
def obtener_docente(docente_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM docentes WHERE id = ?", (docente_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    return dict(row)

class DocenteUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    materia: Optional[str] = None
    dedicacion: Optional[str] = None
    cv_resumen: Optional[str] = None

# 4. Modificar un docente existente
@app.put("/docentes/{docente_id}")
def modificar_docente(docente_id: int, docente: DocenteUpdate):
    try:
        actualizado = actualizar_docente(
            docente_id=docente_id,
            nombre=docente.nombre,
            email=docente.email,
            materia=docente.materia,
            dedicacion=docente.dedicacion,
            cv_resumen=docente.cv_resumen
        )
        if not actualizado:
            raise HTTPException(status_code=404, detail="Docente no encontrado")
        return {"mensaje": "Docente actualizado con éxito"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 5. Eliminar un docente por ID
@app.delete("/docentes/{docente_id}")
def borrar_docente(docente_id: int):
    eliminado = eliminar_docente(docente_id)
    if not eliminado:
        raise HTTPException(status_code=404, detail="Docente no encontrado")
    return {"mensaje": "Docente eliminado con éxito"}

# 6. Procesamiento de CV mediante Ollama local o respaldo documentado
@app.post("/procesar-cv-ia")
def procesar_cv_ia(data: dict):
    cv_texto = data.get("cv_texto", "")
    docente_id = data.get("docente_id")
    if not cv_texto.strip():
        raise HTTPException(status_code=400, detail="El texto del CV no puede estar vacío.")
    
    # Prompt diseñado para estructurar el perfil del docente
    prompt = f"""
    Analiza el siguiente perfil o currículum de un docente universitario y extrae un resumen claro con:
    1. Habilidades principales o áreas de experiencia técnica/académica.
    2. Nivel o títulos destacados.
    3. Una breve evaluación de su perfil para la cátedra.

    Currículum / Perfil:
    {cv_texto}
    """
    
    resumen = ""
    es_simulado = False

    try:
        # Petición a la API local de Ollama (modelo 'llama3')
        ollama_response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )
        
        if ollama_response.status_code == 200:
            resultado_json = ollama_response.json()
            resumen = resultado_json.get("response", "Sin respuesta de la IA.")
        else:
            raise requests.exceptions.ConnectionError()
            
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # Modo documentado conforme a la consigna 4.5 si Ollama no está encendido en la PC local
        es_simulado = True
        resumen = (
            "📌 **Dictamen Académico Generado por IA:**\n\n"
            "1. **Habilidades Principales:** Sólida experiencia en desarrollo de software, análisis de sistemas y metodologías docentes universitarias.\n"
            "2. **Títulos y Formación:** Formación de grado/posgrado vinculada a carreras tecnológicas y digitales.\n"
            "3. **Evaluación de Pertinencia para Cátedra:** Perfil altamente compatible con los requisitos de la materia. Se recomienda su incorporación formal a la planta docente.\n\n"
            "*(Nota: Ejecutado en modo contingencia/asistido. Para procesar en vivo con LLaMA 3, inicia la app Ollama en tu PC)*"
        )

    # Persistencia en la tabla historial_evaluaciones
    id_eval = registrar_evaluacion_cv(cv_texto, resumen, docente_id=docente_id)

    return {
        "resumen_procesado": resumen,
        "evaluacion_id": id_eval,
        "es_simulado": es_simulado
    }

# 7. Consultar historial de evaluaciones de IA
@app.get("/evaluaciones")
def listar_evaluaciones(docente_id: Optional[int] = None):
    return obtener_historial_evaluaciones(docente_id=docente_id)

# 8. Eliminar una evaluación de IA por ID
@app.delete("/evaluaciones/{evaluacion_id}")
def borrar_evaluacion(evaluacion_id: int):
    try:
        eliminado = eliminar_evaluacion(evaluacion_id)
        if not eliminado:
            raise HTTPException(status_code=404, detail="Evaluación no encontrada")
        return {"mensaje": "Evaluación eliminada con éxito"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# 5. Calcular indicadores de la planta docente
@app.get("/indicadores")
def obtener_indicadores():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM docentes")
    total = cursor.fetchone()["total"]
    conn.close()
    return {
        "total_docentes": total,
        "distribucion": "Exclusiva / Semi-exclusiva / Simple (Métrica base)"
    }