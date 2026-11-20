import json

import pytest
from fastapi.testclient import TestClient

from backend import database as db
from backend import ia


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DATA_DIR", tmp_path)
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "test.db")
    from backend.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def ia_falsa(monkeypatch):
    respuesta = {
        "resumen": "Ingeniera con amplia experiencia en bases de datos y Python.",
        "areas_experiencia": ["Bases de datos", "Python"],
        "titulos": ["Ingeniera en Sistemas"],
        "anios_experiencia": 8,
        "materias_sugeridas": ["Bases de Datos Relacionales", "Materia Inventada"],
    }
    monkeypatch.setattr(ia, "_generar", lambda prompt, formato_json=False:
                        json.dumps(respuesta) if formato_json else "Informe de prueba.")
    return respuesta


NUEVO = {"nombre": "Ing. Ana López", "email": "alopez@uni.edu.ar",
         "materia": "Bases de Datos Relacionales", "dedicacion": "Simple",
         "cv_resumen": "SQL y PostgreSQL"}

CV = ("Ingeniera en Sistemas (UTN) con 8 años de experiencia en bases de datos SQL, "
      "PostgreSQL, modelado relacional y procesos ETL. Programación en Python.")


def test_listar_trae_datos_de_ejemplo(client):
    r = client.get("/docentes")
    assert r.status_code == 200
    assert len(r.json()) == 8


def test_crear_consultar_modificar_eliminar(client):
    r = client.post("/docentes", json=NUEVO)
    assert r.status_code == 201
    docente = r.json()
    assert docente["id"] > 0 and docente["materia_id"] is not None

    assert client.get(f"/docentes/{docente['id']}").json()["email"] == NUEVO["email"]

    r = client.patch(f"/docentes/{docente['id']}", json={"dedicacion": "Exclusiva"})
    assert r.status_code == 200 and r.json()["dedicacion"] == "Exclusiva"
    assert r.json()["nombre"] == NUEVO["nombre"]

    assert client.delete(f"/docentes/{docente['id']}").status_code == 204
    assert client.get(f"/docentes/{docente['id']}").status_code == 404


def test_filtros(client):
    assert all(d["dedicacion"] == "Exclusiva"
               for d in client.get("/docentes", params={"dedicacion": "Exclusiva"}).json())
    r = client.get("/docentes", params={"busqueda": "docker"})
    assert r.status_code == 200 and len(r.json()) >= 1


def test_email_duplicado_devuelve_409(client):
    client.post("/docentes", json=NUEVO)
    r = client.post("/docentes", json=NUEVO)
    assert r.status_code == 409
    assert "Ya existe" in r.json()["detail"]


@pytest.mark.parametrize("campo,valor", [
    ("email", "no-es-un-mail"), ("dedicacion", "Full time"), ("nombre", ""),
])
def test_datos_invalidos_devuelven_422(client, campo, valor):
    r = client.post("/docentes", json={**NUEVO, campo: valor})
    assert r.status_code == 422
    assert campo in r.json()["detail"]


def test_docente_inexistente_404(client):
    assert client.get("/docentes/9999").status_code == 404
    assert client.patch("/docentes/9999", json={"nombre": "Xx"}).status_code == 404
    assert client.delete("/docentes/9999").status_code == 404


def test_patch_vacio_422(client):
    assert client.patch("/docentes/1", json={}).status_code == 422


def test_indicadores(client):
    ind = client.get("/indicadores").json()
    assert ind["total_docentes"] == 8
    assert sum(ind["por_dedicacion"].values()) == 8
    assert ind["horas_semanales_contratadas"] > 0


def test_alerta_materia_sin_cobertura(client):
    d = client.post("/docentes", json={**NUEVO, "materia": "Robótica"}).json()
    client.patch(f"/docentes/{d['id']}", json={"materia": "Bases de Datos Relacionales"})
    alertas = client.get("/alertas").json()
    assert alertas["hay_alertas_altas"] is True
    assert any(a["referencia"] == "Robótica" for a in alertas["alertas"])
    materias = {m["nombre"]: m for m in client.get("/materias").json()}
    assert materias["Robótica"]["cubierta"] is False


def test_analizar_cv_valida_salida_de_la_ia(client, ia_falsa):
    r = client.post("/ia/analizar-cv", json={"cv_texto": CV})
    assert r.status_code == 200
    data = r.json()
    assert data["requiere_revision_humana"] is True
    assert data["origen_ia"]["materias_sugeridas"] == ["Bases de Datos Relacionales"]
    assert any("Materia Inventada" in a for a in data["advertencias"])
    assert data["compatibilidad_reglas"][0]["materia"] == "Bases de Datos Relacionales"


def test_cv_muy_corto_422(client):
    assert client.post("/ia/analizar-cv", json={"cv_texto": "hola"}).status_code == 422


def test_ollama_apagado_devuelve_503(client, monkeypatch):
    monkeypatch.setattr(ia, "OLLAMA_URL", "http://127.0.0.1:1")
    r = client.post("/ia/analizar-cv", json={"cv_texto": CV})
    assert r.status_code == 503
    assert "Ollama" in r.json()["detail"]


def test_ia_responde_basura_502(client, monkeypatch):
    monkeypatch.setattr(ia, "_generar", lambda prompt, formato_json=False: "no es json")
    assert client.post("/ia/analizar-cv", json={"cv_texto": CV}).status_code == 502


def test_confirmar_evaluacion_actualiza_docente(client):
    r = client.post("/evaluaciones", json={
        "cv_texto": CV, "resumen_aprobado": "Perfil revisado y aprobado por RRHH.", "docente_id": 2})
    assert r.status_code == 201
    assert r.json()["docente_id"] == 2
    assert client.get("/docentes/2").json()["cv_resumen"] == "Perfil revisado y aprobado por RRHH."
    assert len(client.get("/docentes/2/evaluaciones").json()) >= 1


def test_evaluacion_docente_inexistente_404(client):
    r = client.post("/evaluaciones", json={
        "cv_texto": CV, "resumen_aprobado": "Perfil revisado.", "docente_id": 999})
    assert r.status_code == 404


def test_reporte_ia(client, ia_falsa):
    r = client.post("/ia/reporte")
    assert r.status_code == 200
    assert r.json()["reporte"] == "Informe de prueba."


def test_endpoint_compatibilidad_frontend(client, ia_falsa):
    r = client.post("/procesar-cv-ia", json={"cv_texto": CV})
    assert r.status_code == 200 and "resumen_procesado" in r.json()


def test_put_docente_como_usa_el_frontend(client):
    r = client.put("/docentes/1", json={"dedicacion": "Exclusiva"})
    assert r.status_code == 200 and r.json()["dedicacion"] == "Exclusiva"


def test_procesar_cv_guarda_y_devuelve_evaluacion(client, ia_falsa):
    r = client.post("/procesar-cv-ia", json={"cv_texto": CV, "docente_id": 1})
    data = r.json()
    assert r.status_code == 200 and data["es_simulado"] is False and data["evaluacion_id"] > 0
    assert client.get("/docentes/1").json()["cv_resumen"] == ia_falsa["resumen"]
    assert client.delete(f"/evaluaciones/{data['evaluacion_id']}").status_code == 200
    assert client.delete(f"/evaluaciones/{data['evaluacion_id']}").status_code == 404


def test_procesar_cv_modo_contingencia_sin_ollama(client, monkeypatch):
    monkeypatch.setattr(ia, "OLLAMA_URL", "http://127.0.0.1:1")
    perfil_antes = client.get("/docentes/1").json()["cv_resumen"]
    r = client.post("/procesar-cv-ia", json={"cv_texto": CV, "docente_id": 1, })
    data = r.json()
    assert r.status_code == 200 and data["es_simulado"] is True
    assert "reglas" in data["resumen_procesado"]
    assert client.get("/docentes/1").json()["cv_resumen"] == perfil_antes
    assert client.get("/evaluaciones").json()[0]["id"] == data["evaluacion_id"]
