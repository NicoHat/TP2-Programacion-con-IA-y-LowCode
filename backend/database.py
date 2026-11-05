import sqlite3

DB_PATH = "data/docentes.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS docentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL,
            materia TEXT NOT NULL,
            dedicacion TEXT NOT NULL,
            cv_resumen TEXT
        )
    """)
    conn.commit()
    conn.close()