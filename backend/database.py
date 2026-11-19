import os
import sqlite3
from pathlib import Path
# 1. RUTA DE LA BASE DE DATOS
# Calculamos la ruta absoluta hacia la carpeta "data/" en la raíz del proyecto
# para que nunca falle sin importar desde dónde se ejecute el programa.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "docentes.db"
# 2. CONEXIÓN A SQLITE
def get_connection():
    """
    Crea la carpeta 'data/' si no existe, abre la conexión con SQLite
    y activa el soporte de Claves Foráneas (Foreign Keys).
    Maneja errores de sistema de archivos o de conexión a SQLite.
    """
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        # En SQLite las claves foráneas vienen desactivadas por defecto; acá las activamos:
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except (sqlite3.Error, OSError) as e:
        print(f"Error crítico al conectar con la base de datos en {DB_PATH}: {e}")
        raise RuntimeError(f"No se pudo establecer la conexión con la base de datos: {e}")
# 3. CREACIÓN DE TABLAS Y ESQUEMA RELACIONAL
def init_db():
    """
    Crea las tablas del sistema (materias, docentes, historial_evaluaciones)
    asegurando claves primarias, claves foráneas y restricciones de integridad.
    Luego ejecuta el Seeding inicial si la base está vacía.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Tabla 1: Materias / Cátedras
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL UNIQUE,
                departamento TEXT NOT NULL,
                cuatrimestre TEXT NOT NULL,
                horas_semanales INTEGER NOT NULL DEFAULT 4 CHECK(horas_semanales > 0)
            )
        """)    
        # Tabla 2: Docentes (compatible con main.py y relacionada con materias)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS docentes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                materia TEXT NOT NULL,
                materia_id INTEGER,
                dedicacion TEXT NOT NULL CHECK(dedicacion IN ('Simple', 'Semi-exclusiva', 'Exclusiva')),
                cv_resumen TEXT DEFAULT '',
                fecha_alta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (materia_id) REFERENCES materias(id) ON DELETE SET NULL
            )
        """)
        # Tabla 3: Historial de Evaluaciones / Métricas de IA por docente
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historial_evaluaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                docente_id INTEGER,
                cv_texto_original TEXT NOT NULL,
                resumen_ia TEXT NOT NULL,
                fecha_evaluacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (docente_id) REFERENCES docentes(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error al crear las tablas: {e}")
        raise
    finally:
        conn.close()
    # Una vez creadas las tablas, cargamos los datos iniciales si está vacía
    seed_db()
# 4. DATOS DE PRUEBA INICIALES (SEEDING)
def seed_db():
    """
    Carga materias, docentes de distintas cátedras y dedicaciones, y evaluaciones
    de prueba únicamente cuando la base de datos está vacía (COUNT == 0).
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Verificamos si ya hay docentes cargados para no duplicar datos al reiniciar
        cursor.execute("SELECT COUNT(*) as total FROM docentes")
        if cursor.fetchone()["total"] > 0:
            return
        # A. Cargar materias iniciales
        materias_iniciales = [
            ("Elementos de Programación IA y LowCode", "Inteligencia Artificial y Datos", "2do Cuatrimestre", 6),
            ("Bases de Datos Relacionales", "Sistemas e Informática", "1er Cuatrimestre", 6),
            ("Ingeniería de Software I", "Sistemas e Informática", "1er Cuatrimestre", 4),
            ("Algoritmos y Estructuras de Datos", "Programación", "Anual", 8),
            ("Matemática Discreta", "Ciencias Exactas", "1er Cuatrimestre", 4),
            ("Arquitectura de Computadoras y Redes", "Infraestructura", "2do Cuatrimestre", 4),
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO materias (nombre, departamento, cuatrimestre, horas_semanales)
            VALUES (?, ?, ?, ?)
            """,
            materias_iniciales,
        )
        # Buscamos los IDs de cada materia para relacionar la Foreign Key (materia_id)
        cursor.execute("SELECT id, nombre FROM materias")
        mapa_materias = {fila["nombre"]: fila["id"] for fila in cursor.fetchall()}
        # B. Cargar 8 docentes realistas con distintas cátedras, dedicaciones y CVs
        docentes_iniciales = [
            (
                "Dra. Valeria Gómez",
                "vgomez@universidad.edu.ar",
                "Elementos de Programación IA y LowCode",
                mapa_materias.get("Elementos de Programación IA y LowCode"),
                "Exclusiva",
                "Doctora en Ciencias de la Computación (UBA). 10 años de experiencia en Machine Learning, "
                "procesamiento del lenguaje natural (NLP), LLMs con Ollama y automatización con n8n y Python.",
            ),
            (
                "Mg. Martín Rodríguez",
                "mrodriguez@universidad.edu.ar",
                "Bases de Datos Relacionales",
                mapa_materias.get("Bases de Datos Relacionales"),
                "Semi-exclusiva",
                "Magíster en Ingeniería de Datos. Especialista en modelado relacional, optimización de consultas SQL, "
                "SQLite, PostgreSQL y arquitectura de persistencia.",
            ),
            (
                "Ing. Carolina Fernández",
                "cfernandez@universidad.edu.ar",
                "Ingeniería de Software I",
                mapa_materias.get("Ingeniería de Software I"),
                "Semi-exclusiva",
                "Ingeniera en Sistemas de Información (UTN). Líder técnica con 8 años en desarrollo de APIs REST "
                "con FastAPI, microservicios en Docker y metodologías ágiles.",
            ),
            (
                "Lic. Lucas Morales",
                "lmorales@universidad.edu.ar",
                "Algoritmos y Estructuras de Datos",
                mapa_materias.get("Algoritmos y Estructuras de Datos"),
                "Exclusiva",
                "Licenciado en Ciencias de la Computación. Investigador y docente universitario con publicaciones en "
                "complejidad algorítmica, estructuras de grafos y programación en Python y C++.",
            ),
            (
                "Ing. Sofía Peralta",
                "speralta@universidad.edu.ar",
                "Elementos de Programación IA y LowCode",
                mapa_materias.get("Elementos de Programación IA y LowCode"),
                "Simple",
                "Ingeniera en Informática. Desarrolladora Full Stack y consultora en herramientas Low-Code (n8n, Streamlit). "
                "Experiencia integrando webhooks, APIs y asistentes de IA.",
            ),
            (
                "Dr. Alejandro Silva",
                "asilva@universidad.edu.ar",
                "Matemática Discreta",
                mapa_materias.get("Matemática Discreta"),
                "Exclusiva",
                "Doctor en Matemática Aplicada. 15 años de docencia universitaria en lógica proposicional, "
                "teoría de conjuntos, combinatoria y álgebra booleana.",
            ),
            (
                "Esp. Nicolás Cabrera",
                "ncabrera@universidad.edu.ar",
                "Arquitectura de Computadoras y Redes",
                mapa_materias.get("Arquitectura de Computadoras y Redes"),
                "Simple",
                "Especialista en Redes y Seguridad Informática. Administrador de servidores Linux, contenedores "
                "Docker, Docker Compose y redes TCP/IP.",
            ),
            (
                "Lic. Julieta Navarro",
                "jnavarro@universidad.edu.ar",
                "Bases de Datos Relacionales",
                mapa_materias.get("Bases de Datos Relacionales"),
                "Simple",
                "Licenciada en Sistemas. Analista de datos senior con experiencia en procesos ETL, integridad referencial, "
                "migraciones SQL y visualización de indicadores con Streamlit.",
            ),
        ]
        cursor.executemany(
            """
            INSERT INTO docentes (nombre, email, materia, materia_id, dedicacion, cv_resumen)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            docentes_iniciales,
        )
        # C. Cargar 2 evaluaciones iniciales de ejemplo en historial_evaluaciones
        cursor.execute("SELECT id, cv_resumen FROM docentes LIMIT 2")
        for doc in cursor.fetchall():
            cursor.execute(
                """
                INSERT INTO historial_evaluaciones (docente_id, cv_texto_original, resumen_ia)
                VALUES (?, ?, ?)
                """,
                (
                    doc["id"],
                    doc["cv_resumen"],
                    "Evaluación inicial: Perfil académico altamente compatible con los requisitos de la cátedra.",
                ),
            )
        conn.commit()
        print("Seeding completado: se cargaron materias, docentes e historial inicial.")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error durante el seeding: {e}")
        raise
    finally:
        conn.close()


# =====================================================================
# 5. VALIDACIONES Y PROCEDIMIENTOS DE GESTIÓN DE DATOS (CON EXCEPCIONES)
# =====================================================================

DEDICACIONES_VALIDAS = ("Simple", "Semi-exclusiva", "Exclusiva")


def validar_datos_docente(nombre, email, materia, dedicacion):
    """
    Valida que los datos del docente sean correctos antes de tocar la base de datos.
    Lanza ValueError con un mensaje claro si algún dato es inválido.
    """
    if not nombre or not str(nombre).strip():
        raise ValueError("El nombre del docente no puede estar vacío.")

    if not email or not str(email).strip():
        raise ValueError("El correo electrónico no puede estar vacío.")

    email_limpio = str(email).strip()
    if "@" not in email_limpio or "." not in email_limpio.split("@")[-1]:
        raise ValueError(f"El correo electrónico '{email_limpio}' no tiene un formato válido.")

    if not materia or not str(materia).strip():
        raise ValueError("La materia asignada no puede estar vacía.")

    dedicacion_limpia = str(dedicacion).strip()
    if dedicacion_limpia not in DEDICACIONES_VALIDAS:
        raise ValueError(
            f"La dedicación '{dedicacion_limpia}' no es válida. "
            f"Valores permitidos: {', '.join(DEDICACIONES_VALIDAS)}."
        )


def _obtener_o_crear_materia_id(cursor, nombre_materia):
    """
    Procedimiento auxiliar: busca el ID de una materia por nombre.
    Si no existe en la tabla 'materias', la crea automáticamente.
    """
    nombre_limpio = str(nombre_materia).strip()
    if not nombre_limpio:
        raise ValueError("El nombre de la materia no puede estar vacío.")

    cursor.execute("SELECT id FROM materias WHERE LOWER(nombre) = LOWER(?)", (nombre_limpio,))
    fila = cursor.fetchone()
    if fila:
        return fila["id"]

    cursor.execute(
        """
        INSERT INTO materias (nombre, departamento, cuatrimestre, horas_semanales)
        VALUES (?, 'Departamento General', 'Cuatrimestral', 4)
        """,
        (nombre_limpio,),
    )
    return cursor.lastrowid


# --- A. PROCEDIMIENTOS DE CONSULTA, BÚSQUEDA Y FILTRADO ---

def obtener_docentes(materia=None, dedicacion=None, busqueda=None):
    """
    Devuelve la lista de docentes permitiendo filtrar por materia, dedicación o búsqueda.
    Maneja excepciones de consulta en SQLite.
    """
    if dedicacion and str(dedicacion).strip() not in DEDICACIONES_VALIDAS:
        raise ValueError(
            f"Filtro de dedicación inválido ('{dedicacion}'). "
            f"Use: {', '.join(DEDICACIONES_VALIDAS)}."
        )

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT * FROM docentes WHERE 1=1"
        parametros = []

        if materia and str(materia).strip():
            query += " AND LOWER(materia) LIKE LOWER(?)"
            parametros.append(f"%{str(materia).strip()}%")

        if dedicacion and str(dedicacion).strip():
            query += " AND dedicacion = ?"
            parametros.append(str(dedicacion).strip())

        if busqueda and str(busqueda).strip():
            query += " AND (LOWER(nombre) LIKE LOWER(?) OR LOWER(email) LIKE LOWER(?) OR LOWER(cv_resumen) LIKE LOWER(?))"
            termino = f"%{str(busqueda).strip()}%"
            parametros.extend([termino, termino, termino])

        query += " ORDER BY id DESC"
        cursor.execute(query, parametros)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error en la base de datos al consultar docentes: {e}")
        raise RuntimeError(f"No se pudo consultar el listado de docentes: {e}")
    finally:
        conn.close()


def obtener_docente_por_id(docente_id):
    """Busca y devuelve un docente por su clave primaria (ID)."""
    if not isinstance(docente_id, int) or docente_id <= 0:
        raise ValueError("El ID del docente debe ser un número entero positivo.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM docentes WHERE id = ?", (docente_id,))
        fila = cursor.fetchone()
        return dict(fila) if fila else None
    except sqlite3.Error as e:
        print(f"Error al buscar el docente con ID {docente_id}: {e}")
        raise RuntimeError(f"Error de base de datos al buscar docente: {e}")
    finally:
        conn.close()


def listar_materias():
    """Devuelve todas las materias registradas en la base de datos."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM materias ORDER BY nombre ASC")
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al listar las materias: {e}")
        raise RuntimeError(f"No se pudo obtener la lista de materias: {e}")
    finally:
        conn.close()


# --- B. PROCEDIMIENTOS DE ALTA, MODIFICACIÓN Y BAJA (ABM / CRUD) ---

def crear_nuevo_docente(nombre, email, materia, dedicacion, cv_resumen=""):
    """
    Valida e inserta un nuevo docente vinculándolo con la tabla 'materias'.
    Captura específicamente errores de email duplicado (IntegrityError) y de SQLite.
    """
    validar_datos_docente(nombre, email, materia, dedicacion)

    conn = get_connection()
    cursor = conn.cursor()
    try:
        materia_id = _obtener_o_crear_materia_id(cursor, materia)
        cursor.execute(
            """
            INSERT INTO docentes (nombre, email, materia, materia_id, dedicacion, cv_resumen)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(nombre).strip(),
                str(email).strip(),
                str(materia).strip(),
                materia_id,
                str(dedicacion).strip(),
                str(cv_resumen or "").strip(),
            ),
        )
        nuevo_id = cursor.lastrowid
        conn.commit()
        return nuevo_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        if "UNIQUE" in str(e).upper() or "EMAIL" in str(e).upper():
            raise ValueError(f"Ya existe un docente registrado con el email '{email.strip()}'.")
        raise ValueError(f"Error de integridad de datos al registrar el docente: {e}")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error de SQLite al crear docente: {e}")
        raise RuntimeError(f"Error interno de base de datos al guardar el docente: {e}")
    finally:
        conn.close()


def actualizar_docente(docente_id, nombre=None, email=None, materia=None, dedicacion=None, cv_resumen=None):
    """
    Modifica los datos de un docente existente validando que los nuevos valores
    respeten las reglas de negocio e integridad.
    """
    if not isinstance(docente_id, int) or docente_id <= 0:
        raise ValueError("El ID del docente debe ser un número entero positivo.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM docentes WHERE id = ?", (docente_id,))
        actual = cursor.fetchone()
        if not actual:
            return False

        nuevo_nombre = str(nombre).strip() if nombre is not None else actual["nombre"]
        nuevo_email = str(email).strip() if email is not None else actual["email"]
        nueva_materia = str(materia).strip() if materia is not None else actual["materia"]
        nueva_dedicacion = str(dedicacion).strip() if dedicacion is not None else actual["dedicacion"]
        nuevo_cv = str(cv_resumen).strip() if cv_resumen is not None else actual["cv_resumen"]

        validar_datos_docente(nuevo_nombre, nuevo_email, nueva_materia, nueva_dedicacion)
        nuevo_materia_id = _obtener_o_crear_materia_id(cursor, nueva_materia)

        cursor.execute(
            """
            UPDATE docentes
            SET nombre = ?, email = ?, materia = ?, materia_id = ?, dedicacion = ?, cv_resumen = ?
            WHERE id = ?
            """,
            (nuevo_nombre, nuevo_email, nueva_materia, nuevo_materia_id, nueva_dedicacion, nuevo_cv, docente_id),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"No se pudo actualizar: el email '{nuevo_email}' ya pertenece a otro docente.")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error de SQLite al actualizar docente {docente_id}: {e}")
        raise RuntimeError(f"Error interno al actualizar el docente: {e}")
    finally:
        conn.close()


def eliminar_docente(docente_id):
    """
    Elimina un docente por su ID y limpia su historial asociado (ON DELETE CASCADE).
    """
    if not isinstance(docente_id, int) or docente_id <= 0:
        raise ValueError("El ID del docente debe ser un número entero positivo.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM docentes WHERE id = ?", (docente_id,))
        eliminado = cursor.rowcount > 0
        conn.commit()
        return eliminado
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error de SQLite al eliminar docente {docente_id}: {e}")
        raise RuntimeError(f"No se pudo eliminar el docente de la base de datos: {e}")
    finally:
        conn.close()


# --- C. PROCEDIMIENTOS PARA CV CON IA E INDICADORES ---

def registrar_evaluacion_cv(cv_texto_original, resumen_ia, docente_id=None):
    """
    Guarda en 'historial_evaluaciones' el resultado del análisis de un CV por IA.
    Valida que el texto original y el resumen no estén vacíos y que el docente exista.
    """
    if not cv_texto_original or not str(cv_texto_original).strip():
        raise ValueError("El texto original del CV no puede estar vacío.")
    if not resumen_ia or not str(resumen_ia).strip():
        raise ValueError("El resumen generado por la IA no puede estar vacío.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if docente_id is not None:
            cursor.execute("SELECT id FROM docentes WHERE id = ?", (docente_id,))
            if not cursor.fetchone():
                raise ValueError(f"No existe ningún docente con ID {docente_id} para asociar la evaluación.")

        cursor.execute(
            """
            INSERT INTO historial_evaluaciones (docente_id, cv_texto_original, resumen_ia)
            VALUES (?, ?, ?)
            """,
            (docente_id, str(cv_texto_original).strip(), str(resumen_ia).strip()),
        )
        evaluacion_id = cursor.lastrowid

        if docente_id is not None:
            cursor.execute(
                "UPDATE docentes SET cv_resumen = ? WHERE id = ?",
                (str(resumen_ia).strip(), docente_id),
            )

        conn.commit()
        return evaluacion_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Error de clave foránea al asociar la evaluación al docente: {e}")
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error de SQLite al guardar evaluación de CV: {e}")
        raise RuntimeError(f"No se pudo guardar la evaluación del CV en la base de datos: {e}")
    finally:
        conn.close()


def calcular_indicadores():
    """
    Calcula métricas reales de la planta docente desde SQLite con manejo de errores.
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as total FROM docentes")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT dedicacion, COUNT(*) as cantidad FROM docentes GROUP BY dedicacion")
        por_dedicacion = {fila["dedicacion"]: fila["cantidad"] for fila in cursor.fetchall()}
        for cat in DEDICACIONES_VALIDAS:
            por_dedicacion.setdefault(cat, 0)

        cursor.execute("SELECT materia, COUNT(*) as cantidad FROM docentes GROUP BY materia ORDER BY cantidad DESC")
        por_materia = {fila["materia"]: fila["cantidad"] for fila in cursor.fetchall()}

        texto_distribucion = (
            f"Exclusiva: {por_dedicacion['Exclusiva']} | "
            f"Semi-exclusiva: {por_dedicacion['Semi-exclusiva']} | "
            f"Simple: {por_dedicacion['Simple']}"
        )

        return {
            "total_docentes": total,
            "distribucion": texto_distribucion,
            "por_dedicacion": por_dedicacion,
            "por_materia": por_materia,
        }
    except sqlite3.Error as e:
        print(f"Error al calcular indicadores: {e}")
        raise RuntimeError(f"No se pudieron calcular los indicadores de la planta docente: {e}")
    finally:
        conn.close()


def obtener_historial_evaluaciones(docente_id=None):
    """
    Devuelve el historial de evaluaciones de CV realizadas con IA, incluyendo
    el nombre y materia del docente mediante un LEFT JOIN.
    Si se indica docente_id, filtra solo el historial de ese docente.
    """
    if docente_id is not None and (not isinstance(docente_id, int) or docente_id <= 0):
        raise ValueError("El ID del docente debe ser un número entero positivo.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
            SELECT h.id, h.docente_id, d.nombre AS docente_nombre, d.materia,
                   h.cv_texto_original, h.resumen_ia, h.fecha_evaluacion
            FROM historial_evaluaciones h
            LEFT JOIN docentes d ON h.docente_id = d.id
        """
        parametros = []
        if docente_id is not None:
            query += " WHERE h.docente_id = ?"
            parametros.append(docente_id)

        query += " ORDER BY h.fecha_evaluacion DESC, h.id DESC"
        cursor.execute(query, parametros)
        return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error al consultar el historial de evaluaciones: {e}")
        raise RuntimeError(f"No se pudo obtener el historial de evaluaciones: {e}")
    finally:
        conn.close()


def eliminar_evaluacion(evaluacion_id: int) -> bool:
    """
    Elimina un registro de evaluación de la tabla historial_evaluaciones.
    Devuelve True si se eliminó, o False si el ID no existía.
    """
    if not isinstance(evaluacion_id, int) or evaluacion_id <= 0:
        raise ValueError("El ID de la evaluación debe ser un número entero positivo.")

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM historial_evaluaciones WHERE id = ?", (evaluacion_id,))
        eliminado = cursor.rowcount > 0
        conn.commit()
        return eliminado
    except sqlite3.Error as e:
        conn.rollback()
        print(f"Error al eliminar la evaluación #{evaluacion_id}: {e}")
        raise RuntimeError(f"No se pudo eliminar la evaluación: {e}")
    finally:
        conn.close()


# Permite ejecutar este archivo directamente (python backend/database.py)
# para crear y poblar la base de datos de inmediato.
if __name__ == "__main__":
    init_db()
    print(f"Base de datos lista en: {DB_PATH}")