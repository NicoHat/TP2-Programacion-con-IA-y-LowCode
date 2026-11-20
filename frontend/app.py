import io
import os

import requests
import streamlit as st

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
DEDICACIONES = ["Simple", "Semi-exclusiva", "Exclusiva"]
NUEVA_MATERIA = "➕ Otra materia (nueva)"

st.set_page_config(page_title="Sistema de Gestión de Planta Docente", page_icon="🎓", layout="wide")


def api(metodo, ruta, timeout=10, **kwargs):
    try:
        r = requests.request(metodo, f"{API_URL}{ruta}", timeout=timeout, **kwargs)
    except requests.exceptions.ConnectionError:
        return None, {"detail": f"No se pudo conectar con la API en {API_URL}. Verificá que esté iniciada."}
    except requests.exceptions.Timeout:
        return None, {"detail": "La API tardó demasiado en responder."}
    try:
        datos = r.json()
    except ValueError:
        datos = {}
    return r.status_code, datos


def detalle(datos):
    if isinstance(datos, dict):
        return datos.get("detail", "Error desconocido.")
    return "Error desconocido."


def mostrar_error(codigo, datos, prefijo=""):
    mensaje = detalle(datos)
    if codigo is None:
        st.error(f"🔌 {mensaje}")
    elif codigo == 404:
        st.warning(f"🔎 {prefijo}{mensaje}")
    elif codigo in (400, 409, 422):
        st.error(f"⚠️ {prefijo}{mensaje} (código {codigo})")
    elif codigo in (502, 503, 504):
        st.error(f"🤖 {prefijo}{mensaje} (código {codigo})")
    else:
        st.error(f"❌ {prefijo}{mensaje} (código {codigo})")


def catalogo_materias():
    codigo, datos = api("GET", "/materias")
    return datos if codigo == 200 else []


def selector_materia(etiqueta, materias, actual=None, key=None):
    nombres = [m["nombre"] for m in materias]
    opciones = nombres + [NUEVA_MATERIA]
    indice = nombres.index(actual) if actual in nombres else 0
    eleccion = st.selectbox(etiqueta, opciones, index=indice, key=key)
    nueva = st.text_input("Nombre de la nueva materia", key=f"{key}_nueva" if key else None,
                          placeholder="Solo si elegiste «Otra materia»")
    return nueva.strip() if eleccion == NUEVA_MATERIA else eleccion


def formato_pesos(valor):
    return "$ " + f"{valor:,.0f}".replace(",", ".")


def leer_archivo_cv(archivo):
    if archivo.name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        lector = PdfReader(io.BytesIO(archivo.getvalue()))
        return "\n".join((pagina.extract_text() or "") for pagina in lector.pages).strip()
    return archivo.getvalue().decode("utf-8", errors="ignore").strip()


st.sidebar.title("🎓 Planta Docente")
opcion = st.sidebar.radio(
    "Sección",
    ["👥 Planta Docente", "➕ Registrar Docente", "📊 Indicadores y Alertas", "🤖 Análisis de CV con IA"],
)

st.sidebar.divider()
codigo_salud, salud = api("GET", "/health", timeout=4)
if codigo_salud == 200:
    st.sidebar.success(f"API conectada · {salud.get('docentes', 0)} docentes")
    if salud.get("ollama") == "ok" and salud.get("modelo_descargado"):
        st.sidebar.success(f"IA disponible · {salud.get('modelo')}")
    elif salud.get("ollama") == "ok":
        st.sidebar.warning(f"Ollama activo, falta el modelo {salud.get('modelo')}")
    else:
        st.sidebar.warning("IA no disponible (Ollama apagado)")
else:
    st.sidebar.error("API no disponible")


if opcion == "👥 Planta Docente":
    st.header("👥 Planta Docente")

    materias = catalogo_materias()
    c1, c2, c3 = st.columns([3, 2, 2])
    busqueda = c1.text_input("🔍 Buscar", placeholder="Nombre, email o antecedentes")
    filtro_materia = c2.selectbox("Materia", ["Todas"] + [m["nombre"] for m in materias])
    filtro_dedicacion = c3.selectbox("Dedicación", ["Todas"] + DEDICACIONES)

    parametros = {}
    if busqueda.strip():
        parametros["busqueda"] = busqueda.strip()
    if filtro_materia != "Todas":
        parametros["materia"] = filtro_materia
    if filtro_dedicacion != "Todas":
        parametros["dedicacion"] = filtro_dedicacion

    codigo, docentes = api("GET", "/docentes", params=parametros)
    if codigo != 200:
        mostrar_error(codigo, docentes)
        st.stop()

    st.caption(f"{len(docentes)} docente(s) encontrados")
    if not docentes:
        st.info("No hay docentes que coincidan con los filtros.")

    for doc in docentes:
        doc_id = doc["id"]
        with st.expander(f"👨‍🏫 {doc['nombre']} — {doc['materia']} ({doc['dedicacion']})"):
            info, acciones = st.columns([4, 1])
            with info:
                st.markdown(f"**Email:** `{doc['email']}`")
                st.markdown(f"**Materia:** {doc['materia']}  ·  **Dedicación:** {doc['dedicacion']}")
                st.markdown(f"**Alta:** {doc.get('fecha_alta') or '-'}")
                st.markdown(f"**Perfil:** {doc.get('cv_resumen') or '_Sin antecedentes cargados._'}")
            with acciones:
                confirmar = st.checkbox("Confirmar baja", key=f"conf_{doc_id}")
                if st.button("🗑️ Eliminar", key=f"del_{doc_id}", disabled=not confirmar):
                    codigo_del, datos_del = api("DELETE", f"/docentes/{doc_id}")
                    if codigo_del == 204:
                        st.toast(f"Docente #{doc_id} eliminado")
                        st.rerun()
                    else:
                        mostrar_error(codigo_del, datos_del)

            if st.toggle("Ver evaluaciones de CV", key=f"ev_{doc_id}"):
                codigo_ev, evaluaciones = api("GET", f"/docentes/{doc_id}/evaluaciones")
                if codigo_ev != 200:
                    mostrar_error(codigo_ev, evaluaciones)
                elif not evaluaciones:
                    st.caption("Sin evaluaciones registradas.")
                else:
                    for ev in evaluaciones:
                        st.markdown(f"**#{ev['id']}** · {ev.get('fecha_evaluacion', '')}")
                        st.write(ev.get("resumen_ia", ""))

            if st.toggle("✏️ Editar", key=f"ed_{doc_id}"):
                with st.form(f"form_editar_{doc_id}"):
                    e1, e2 = st.columns(2)
                    with e1:
                        nuevo_nombre = st.text_input("Nombre y apellido", value=doc["nombre"])
                        nuevo_email = st.text_input("Email", value=doc["email"])
                    with e2:
                        nueva_materia = selector_materia("Materia", materias, doc["materia"], key=f"mat_{doc_id}")
                        nueva_dedicacion = st.selectbox(
                            "Dedicación", DEDICACIONES,
                            index=DEDICACIONES.index(doc["dedicacion"]) if doc["dedicacion"] in DEDICACIONES else 0,
                        )
                    nuevo_cv = st.text_area("Perfil / antecedentes", value=doc.get("cv_resumen") or "")
                    if st.form_submit_button("💾 Guardar cambios"):
                        cambios = {
                            "nombre": nuevo_nombre.strip(),
                            "email": nuevo_email.strip(),
                            "materia": nueva_materia,
                            "dedicacion": nueva_dedicacion,
                            "cv_resumen": nuevo_cv.strip(),
                        }
                        codigo_put, datos_put = api("PUT", f"/docentes/{doc_id}", json=cambios)
                        if codigo_put == 200:
                            st.toast("Docente actualizado")
                            st.rerun()
                        else:
                            mostrar_error(codigo_put, datos_put)


elif opcion == "➕ Registrar Docente":
    st.header("➕ Registrar Docente")

    materias = catalogo_materias()
    with st.form("form_alta", clear_on_submit=False):
        c1, c2 = st.columns(2)
        with c1:
            nombre = st.text_input("Nombre y apellido *", placeholder="Lic. Martín Rossi")
            email = st.text_input("Email institucional *", placeholder="mrossi@universidad.edu.ar")
        with c2:
            materia = selector_materia("Materia *", materias, key="alta_materia")
            dedicacion = st.selectbox("Dedicación *", DEDICACIONES)
        cv_resumen = st.text_area("Perfil / antecedentes", placeholder="Formación, experiencia docente y técnica")
        archivo = st.file_uploader("…o cargar el CV desde un archivo", type=["txt", "pdf"])
        enviar = st.form_submit_button("💾 Registrar docente")

    if enviar:
        if archivo is not None and not cv_resumen.strip():
            try:
                cv_resumen = leer_archivo_cv(archivo)[:5000]
            except Exception:
                st.warning("No se pudo leer el archivo; se registra sin antecedentes.")
        if not materia:
            st.error("⚠️ Escribí el nombre de la nueva materia.")
        else:
            codigo, datos = api("POST", "/docentes", json={
                "nombre": nombre.strip(),
                "email": email.strip(),
                "materia": materia,
                "dedicacion": dedicacion,
                "cv_resumen": cv_resumen.strip(),
            })
            if codigo == 201:
                st.success(f"✅ Docente registrado con el ID #{datos['id']}: {datos['nombre']} — {datos['materia']}")
                st.balloons()
            else:
                mostrar_error(codigo, datos, "No se pudo registrar: ")


elif opcion == "📊 Indicadores y Alertas":
    st.header("📊 Indicadores y Alertas")

    codigo, ind = api("GET", "/indicadores")
    if codigo != 200:
        mostrar_error(codigo, ind)
        st.stop()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("👥 Docentes", ind["total_docentes"])
    m2.metric("📚 Materias", ind["total_materias"])
    m3.metric("✅ Cobertura de materias", f"{ind['cobertura_pct']} %")
    m4.metric("➗ Docentes por materia", ind["promedio_docentes_por_materia"])

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("⏱️ Horas semanales contratadas", ind["horas_semanales_contratadas"])
    m6.metric("🏫 Horas semanales de cátedra", ind["horas_semanales_catedra"])
    m7.metric("💰 Costo mensual estimado", formato_pesos(ind["costo_mensual_estimado"]))
    m8.metric("📝 Docentes sin CV", len(ind["docentes_sin_cv"]))

    st.divider()
    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Distribución por dedicación")
        st.bar_chart(ind["por_dedicacion"], horizontal=True)
        st.caption(" · ".join(f"{k}: {v} %" for k, v in ind["porcentaje_dedicacion"].items()))
    with g2:
        st.subheader("Docentes por materia")
        st.bar_chart(ind["por_materia"], horizontal=True)

    st.subheader("Cobertura de materias")
    codigo_m, materias = api("GET", "/materias")
    if codigo_m == 200:
        st.dataframe(
            [{
                "Materia": m["nombre"],
                "Departamento": m["departamento"],
                "Cuatrimestre": m["cuatrimestre"],
                "Horas semanales": m["horas_semanales"],
                "Docentes": m["cantidad_docentes"],
                "Estado": "✅ Cubierta" if m["cubierta"] else "❌ Sin docentes",
            } for m in materias],
            hide_index=True, width="stretch",
        )

    st.divider()
    st.subheader("🚨 Alertas")
    codigo_a, alertas = api("GET", "/alertas")
    if codigo_a != 200:
        mostrar_error(codigo_a, alertas)
    else:
        sev = alertas["por_severidad"]
        a1, a2, a3 = st.columns(3)
        a1.metric("🔴 Altas", sev["alta"])
        a2.metric("🟠 Medias", sev["media"])
        a3.metric("🔵 Bajas", sev["baja"])
        if not alertas["alertas"]:
            st.success("No hay alertas: la planta está en orden.")
        for alerta in alertas["alertas"]:
            if alerta["severidad"] == "alta":
                st.error(f"🔴 {alerta['mensaje']}")
            elif alerta["severidad"] == "media":
                st.warning(f"🟠 {alerta['mensaje']}")
            else:
                st.info(f"🔵 {alerta['mensaje']}")

    st.divider()
    st.subheader("📝 Informe ejecutivo con IA")
    if st.button("Generar informe"):
        with st.spinner("La IA está redactando el informe..."):
            codigo_r, reporte = api("POST", "/ia/reporte", timeout=180)
        if codigo_r == 200:
            st.session_state["reporte_ia"] = reporte["reporte"]
        else:
            mostrar_error(codigo_r, reporte)
    if st.session_state.get("reporte_ia"):
        with st.container(border=True):
            st.markdown(st.session_state["reporte_ia"])
        st.caption("Redactado por IA a partir de los indicadores calculados por el sistema.")


elif opcion == "🤖 Análisis de CV con IA":
    st.header("🤖 Análisis de CV con IA")

    codigo_d, lista_docentes = api("GET", "/docentes")
    lista_docentes = lista_docentes if codigo_d == 200 else []
    opciones = {"Postulante (sin docente asociado)": None}
    opciones.update({f"#{d['id']} · {d['nombre']} ({d['materia']})": d["id"] for d in lista_docentes})

    tab_analizar, tab_historial = st.tabs(["Analizar CV", "Historial"])

    with tab_analizar:
        docente_id = opciones[st.selectbox("Asociar a", list(opciones.keys()))]
        origen = st.radio("Origen del CV", ["Pegar texto", "Subir archivo"], horizontal=True)
        cv_texto = ""
        if origen == "Pegar texto":
            cv_texto = st.text_area("Texto del CV", height=180,
                                    placeholder="Formación, experiencia, tecnologías, antecedentes docentes...")
        else:
            archivo = st.file_uploader("Archivo del CV", type=["txt", "pdf"])
            if archivo is not None:
                try:
                    cv_texto = leer_archivo_cv(archivo)
                    with st.expander(f"Texto extraído ({len(cv_texto)} caracteres)"):
                        st.text(cv_texto[:3000])
                except Exception:
                    st.error("No se pudo leer el archivo.")

        if st.button("🚀 Analizar", type="primary"):
            st.session_state.pop("analisis", None)
            st.session_state.pop("error_ia", None)
            st.session_state.pop("contingencia", None)
            with st.spinner("Analizando el CV..."):
                codigo, datos = api("POST", "/ia/analizar-cv", timeout=180,
                                    json={"cv_texto": cv_texto.strip(), "docente_id": docente_id})
            if codigo == 200:
                st.session_state["analisis"] = {"datos": datos, "cv_texto": cv_texto.strip(), "docente_id": docente_id}
            elif codigo in (503, 504):
                st.session_state["error_ia"] = {"detalle": detalle(datos), "cv_texto": cv_texto.strip(),
                                                "docente_id": docente_id}
            else:
                mostrar_error(codigo, datos)

        if st.session_state.get("error_ia"):
            err = st.session_state["error_ia"]
            st.error(f"🤖 {err['detalle']}")
            if st.button("Registrar solo el análisis por reglas (sin IA)"):
                codigo, datos = api("POST", "/procesar-cv-ia", timeout=60,
                                    json={"cv_texto": err["cv_texto"], "docente_id": err["docente_id"]})
                if codigo == 200:
                    st.session_state.pop("error_ia")
                    st.session_state["contingencia"] = datos
                    st.rerun()
                else:
                    mostrar_error(codigo, datos)

        if st.session_state.get("contingencia"):
            datos = st.session_state.pop("contingencia")
            st.success(f"Evaluación #{datos['evaluacion_id']} registrada en modo contingencia (sin IA).")
            with st.container(border=True):
                st.markdown(datos["resumen_procesado"])

        if st.session_state.get("analisis"):
            analisis = st.session_state["analisis"]
            ia = analisis["datos"]["origen_ia"]
            reglas = analisis["datos"]["compatibilidad_reglas"]
            advertencias = analisis["datos"]["advertencias"]

            col_ia, col_reglas = st.columns(2)
            with col_ia:
                with st.container(border=True):
                    st.subheader("🤖 Generado por IA")
                    st.caption(f"Modelo: {analisis['datos']['modelo']}")
                    st.markdown(f"**Resumen:** {ia['resumen']}")
                    st.markdown("**Áreas de experiencia:** " + (", ".join(ia["areas_experiencia"]) or "-"))
                    st.markdown("**Títulos:** " + (", ".join(ia["titulos"]) or "-"))
                    anios = ia.get("anios_experiencia")
                    st.markdown(f"**Años de experiencia:** {anios if anios is not None else '-'}")
                    st.markdown("**Materias sugeridas:** " + (", ".join(ia["materias_sugeridas"]) or "-"))
            with col_reglas:
                with st.container(border=True):
                    st.subheader("📐 Calculado por reglas")
                    st.caption("Coincidencias entre el CV y el nombre de cada materia")
                    if not reglas:
                        st.info("Sin coincidencias suficientes con el catálogo.")
                    for c in reglas:
                        st.markdown(f"**{c['materia']}** — {c['puntaje']} %")
                        st.progress(c["puntaje"] / 100)
                        st.caption("Coincidencias: " + ", ".join(c["coincidencias"]))

            if advertencias:
                st.warning("**Validación de la respuesta de la IA:**\n\n" + "\n".join(f"- {a}" for a in advertencias))
            else:
                st.success("La respuesta de la IA pasó todas las validaciones.")

            st.subheader("✅ Revisión y aprobación")
            resumen_aprobado = st.text_area("Resumen a registrar (editable)", value=ia["resumen"], height=120)
            b1, b2, _ = st.columns([1, 1, 3])
            if b1.button("Aprobar y guardar", type="primary"):
                codigo, datos = api("POST", "/evaluaciones", json={
                    "cv_texto": analisis["cv_texto"],
                    "resumen_aprobado": resumen_aprobado.strip(),
                    "docente_id": analisis["docente_id"],
                })
                if codigo == 201:
                    st.session_state.pop("analisis")
                    st.toast(f"Evaluación #{datos['id']} guardada")
                    st.rerun()
                else:
                    mostrar_error(codigo, datos)
            if b2.button("Descartar"):
                st.session_state.pop("analisis")
                st.rerun()

    with tab_historial:
        opciones_hist = {"Todas": None}
        opciones_hist.update({k: v for k, v in opciones.items() if v is not None})
        filtro = opciones_hist[st.selectbox("Docente", list(opciones_hist.keys()), key="hist_doc")]
        codigo_h, historial = api("GET", "/evaluaciones", params={"docente_id": filtro} if filtro else None)
        if codigo_h != 200:
            mostrar_error(codigo_h, historial)
        elif not historial:
            st.info("No hay evaluaciones registradas.")
        else:
            st.caption(f"{len(historial)} evaluación(es)")
            for h in historial:
                titulo = h.get("docente_nombre") or "Postulante"
                materia_h = f" — {h['materia']}" if h.get("materia") else ""
                with st.expander(f"📄 #{h['id']} · {titulo}{materia_h} · {h.get('fecha_evaluacion', '')}"):
                    st.markdown("**Resumen registrado:**")
                    st.markdown(h.get("resumen_ia", ""))
                    st.markdown("**CV original:**")
                    st.code(h.get("cv_texto_original", ""), language="text")
                    if st.button("🗑️ Eliminar evaluación", key=f"del_ev_{h['id']}"):
                        codigo_del, datos_del = api("DELETE", f"/evaluaciones/{h['id']}")
                        if codigo_del == 200:
                            st.toast(f"Evaluación #{h['id']} eliminada")
                            st.rerun()
                        else:
                            mostrar_error(codigo_del, datos_del)
