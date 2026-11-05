from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import requests
from backend.database import init_db, get_connection

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

# 4. Procesamiento de CV mediante Ollama local
@app.post("/procesar-cv-ia")
def procesar_cv_ia(data: dict):
    cv_texto = data.get("cv_texto", "")
    
    # Prompt diseñado para estructurar el perfil del docente
    prompt = f"""
    Analiza el siguiente perfil o currículum de un docente universitario y extrae un resumen claro con:
    1. Habilidades principales o áreas de experiencia técnica/académica.
    2. Nivel o títulos destacados.
    3. Una breve evaluación de su perfil para la cátedra.

    Currículum / Perfil:
    {cv_texto}
    """
    
    try:
        # Petición a la API local de Ollama (asegúrate de tener un modelo como 'llama3' descargado)
        ollama_response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3",
                "prompt": prompt,
                "stream": False
            },
            timeout=45
        )
        
        if ollama_response.status_code == 200:
            resultado_json = ollama_response.json()
            return {"resumen_procesado": resultado_json.get("response", "Sin respuesta de la IA.")}
        else:
            return {"resumen_procesado": "Error en la respuesta del servidor de Ollama."}
            
    except requests.exceptions.ConnectionError:
        return {"resumen_procesado": "No se pudo conectar con Ollama. Asegúrate de que la aplicación esté abierta en tu PC."}

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