import streamlit as st
import requests

# ==============================================================================
# CONFIGURACIÓN GENERAL Y CONEXIÓN CON LA API
# ==============================================================================
# URL base de la API FastAPI. Si corre en la misma máquina, se usa localhost en el puerto 8000.
API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="Sistema de Gestión de Planta Docente",
    page_icon="🎓",
    layout="wide"
)

# ==============================================================================
# MENÚ DE NAVEGACIÓN LATERAL (SIDEBAR)
# ==============================================================================
# Usamos un st.sidebar.radio que funciona como un enrutador simple.
# Según la opción seleccionada, el script ejecuta la sección correspondiente.
st.sidebar.title("🎓 Menú Principal")
opcion = st.sidebar.radio(
    "Selecciona una sección:",
    [
        "👥 Planta Docente",
        "➕ Registrar Docente",
        "📊 Panel de Indicadores",
        "🤖 Análisis de CV con IA"
    ]
)

st.sidebar.divider()
st.sidebar.info("💡 **Tip para la defensa**: Este frontend se comunica con FastAPI mediante llamadas HTTP (`GET`, `POST`, `DELETE`).")


# ==============================================================================
# SECCIÓN 1: 👥 PLANTA DOCENTE (Listado, Búsqueda y Eliminación)
# ==============================================================================
if opcion == "👥 Planta Docente":
    st.header("👥 Gestión de Planta Docente")
    st.markdown("Consulta, filtra y administra los profesores registrados en la institución.")

    # Filtros interactivos en columnas para que se vea ordenado
    col_busqueda, col_filtro = st.columns([3, 1])
    with col_busqueda:
        texto_busqueda = st.text_input("🔍 Buscar por nombre, materia o email:", placeholder="Ej: Perez, Sistemas, algoritmos...")
    with col_filtro:
        filtro_dedicacion = st.selectbox("Filtrar por dedicación:", ["Todas", "Simple", "Semi-exclusiva", "Exclusiva"])

    # Llamada a la API mediante GET /docentes
    try:
        respuesta = requests.get(f"{API_URL}/docentes", timeout=5)
        
        if respuesta.status_code == 200:
            docentes = respuesta.json()

            # Aplicamos los filtros en el frontend sobre la lista obtenida
            if filtro_dedicacion != "Todas":
                docentes = [d for d in docentes if d.get("dedicacion") == filtro_dedicacion]
            
            if texto_busqueda:
                termino = texto_busqueda.lower()
                docentes = [
                    d for d in docentes
                    if termino in d.get("nombre", "").lower()
                    or termino in d.get("materia", "").lower()
                    or termino in d.get("email", "").lower()
                ]

            st.write(f"Mostrando **{len(docentes)}** docente(s) registrado(s):")

            if not docentes:
                st.info("No se encontraron docentes con los criterios seleccionados.")
            else:
                # Mostramos cada docente en una tarjeta desplegable (st.expander)
                for doc in docentes:
                    doc_id = doc.get("id")
                    nombre = doc.get("nombre", "Sin nombre")
                    materia = doc.get("materia", "Sin materia")
                    dedicacion = doc.get("dedicacion", "No especificada")
                    email = doc.get("email", "Sin email")
                    cv = doc.get("cv_resumen", "")

                    with st.expander(f"👨‍🏫 {nombre} — {materia} ({dedicacion})"):
                        col_info, col_acciones = st.columns([4, 1])
                        
                        with col_info:
                            st.write(f"📧 **Correo electrónico:** `{email}`")
                            st.write(f"💼 **Dedicación:** {dedicacion}")
                            st.write(f"📝 **Perfil / Antecedentes:** {cv if cv else '_Sin antecedentes cargados._'}")
                        
                        with col_acciones:
                            # Botón para eliminar docente llamando a DELETE /docentes/{id}
                            if st.button("🗑️ Eliminar", key=f"btn_eliminar_{doc_id}"):
                                try:
                                    res_del = requests.delete(f"{API_URL}/docentes/{doc_id}", timeout=5)
                                    if res_del.status_code in [200, 204]:
                                        st.success(f"Docente #{doc_id} eliminado.")
                                        st.rerun()
                                    else:
                                        st.error(f"No se pudo eliminar (Código {res_del.status_code}).")
                                except requests.exceptions.RequestException:
                                    st.error("Error al conectar con la API para eliminar.")

                        # Formulario para editar datos del docente (Llamada HTTP PUT)
                        with st.expander("✏️ Editar datos de este docente"):
                            with st.form(f"form_editar_{doc_id}"):
                                ed_col1, ed_col2 = st.columns(2)
                                nuevo_nombre = ed_col1.text_input("Nombre y Apellido", value=nombre)
                                nuevo_email = ed_col1.text_input("Correo Electrónico", value=email)
                                nueva_materia = ed_col2.text_input("Materia Asignada", value=materia)
                                
                                opciones_ded = ["Simple", "Semi-exclusiva", "Exclusiva"]
                                idx_ded = opciones_ded.index(dedicacion) if dedicacion in opciones_ded else 0
                                nueva_dedicacion = ed_col2.selectbox("Dedicación", opciones_ded, index=idx_ded)
                                nuevo_cv = st.text_area("Perfil / Antecedentes", value=cv)

                                guardar_edicion = st.form_submit_button("💾 Guardar Cambios")

                                if guardar_edicion:
                                    if not nuevo_nombre.strip() or not nuevo_email.strip() or not nueva_materia.strip():
                                        st.warning("⚠️ El nombre, email y materia no pueden estar vacíos.")
                                    else:
                                        payload_update = {
                                            "nombre": nuevo_nombre.strip(),
                                            "email": nuevo_email.strip(),
                                            "materia": nueva_materia.strip(),
                                            "dedicacion": nueva_dedicacion,
                                            "cv_resumen": nuevo_cv.strip()
                                        }
                                        try:
                                            res_put = requests.put(f"{API_URL}/docentes/{doc_id}", json=payload_update, timeout=5)
                                            if res_put.status_code == 200:
                                                st.success("✅ ¡Docente actualizado con éxito!")
                                                st.rerun()
                                            else:
                                                st.error(f"❌ Error al actualizar: {res_put.json().get('detail', 'Error desconocido')}")
                                        except requests.exceptions.RequestException:
                                            st.error("❌ Error de conexión al intentar actualizar.")
        else:
            st.error(f"Error al obtener docentes desde la API (Código HTTP {respuesta.status_code}).")

    except requests.exceptions.ConnectionError:
        st.error("❌ No se pudo conectar con el servidor de FastAPI. Verifica que esté iniciado (`uvicorn backend.main:app`).")
    except requests.exceptions.Timeout:
        st.error("⏳ La petición a la API tardó demasiado tiempo en responder.")


# ==============================================================================
# SECCIÓN 2: ➕ REGISTRAR DOCENTE (Formulario con Validaciones)
# ==============================================================================
elif opcion == "➕ Registrar Docente":
    st.header("➕ Registro de Nuevo Docente")
    st.markdown("Completa el formulario para dar de alta un nuevo docente en el sistema.")

    with st.form("form_alta_docente", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Nombre y Apellido *", placeholder="Ej: Lic. Martín Rossi")
            email = st.text_input("Correo Electrónico Institucional *", placeholder="Ej: mrossi@universidad.edu.ar")
        with col2:
            materia = st.text_input("Materia Asignada *", placeholder="Ej: Elementos de Programación IA")
            dedicacion = st.selectbox("Dedicación *", ["Simple", "Semi-exclusiva", "Exclusiva"])

        cv_resumen = st.text_area("Perfil / Antecedentes Curriculares:", placeholder="Resumen de experiencia docente o técnica...")

        enviar = st.form_submit_button("💾 Guardar Docente")

        if enviar:
            # Validaciones previas en el Frontend
            if not nombre.strip() or not email.strip() or not materia.strip():
                st.warning("⚠️ Los campos con asterisco (*) son obligatorios.")
            elif "@" not in email or "." not in email:
                st.warning("⚠️ Por favor ingresa un correo electrónico válido (ejemplo@dominio.com).")
            else:
                # Construcción del payload JSON a enviar a FastAPI
                payload = {
                    "nombre": nombre.strip(),
                    "email": email.strip(),
                    "materia": materia.strip(),
                    "dedicacion": dedicacion,
                    "cv_resumen": cv_resumen.strip()
                }

                try:
                    respuesta = requests.post(f"{API_URL}/docentes", json=payload, timeout=5)
                    
                    if respuesta.status_code in [200, 201]:
                        st.success("✅ ¡Docente registrado con éxito!")
                        st.balloons()
                    elif respuesta.status_code in (400, 409, 422):
                        detalle = respuesta.json().get("detail", "Datos inválidos.")
                        st.error(f"⚠️ Error de validación: {detalle}")
                    else:
                        st.error(f"❌ Error al registrar docente (Código {respuesta.status_code}).")
                except requests.exceptions.ConnectionError:
                    st.error("❌ No se pudo conectar con FastAPI. Revisa que el backend esté encendido.")


# ==============================================================================
# SECCIÓN 3: 📊 PANEL DE INDICADORES (Métricas Institucionales)
# ==============================================================================
elif opcion == "📊 Panel de Indicadores":
    st.header("📊 Panel de Indicadores de Planta Docente")
    st.markdown("Visualización de métricas generales calculadas por el sistema.")

    try:
        # Obtenemos los indicadores desde la API
        res_ind = requests.get(f"{API_URL}/indicadores", timeout=5)
        # Obtenemos también la lista para calcular distribuciones visuales
        res_doc = requests.get(f"{API_URL}/docentes", timeout=5)

        if res_ind.status_code == 200 and res_doc.status_code == 200:
            datos_ind = res_ind.json()
            docentes = res_doc.json()
            total_docentes = datos_ind.get("total_docentes", len(docentes))

            # Métricas principales en tarjetas (st.metric)
            m1, m2, m3, m4 = st.columns(4)
            simples = sum(1 for d in docentes if d.get("dedicacion") == "Simple")
            semi = sum(1 for d in docentes if d.get("dedicacion") == "Semi-exclusiva")
            exclusivas = sum(1 for d in docentes if d.get("dedicacion") == "Exclusiva")

            m1.metric("👥 Total Docentes", total_docentes)
            m2.metric("🟢 Dedicación Simple", simples)
            m3.metric("🟡 Semi-exclusiva", semi)
            m4.metric("🟣 Exclusiva", exclusivas)

            st.divider()

            # Distribución gráfica por Dedicación
            st.subheader("Distribución por Tipo de Dedicación")
            datos_dedicacion = {
                "Simple": simples,
                "Semi-exclusiva": semi,
                "Exclusiva": exclusivas
            }
            st.bar_chart(datos_dedicacion)

            # Resumen de docentes por materia
            st.subheader("Docentes por Asignatura")
            materias_conteo = {}
            for d in docentes:
                mat = d.get("materia", "Sin materia")
                materias_conteo[mat] = materias_conteo.get(mat, 0) + 1
            
            st.dataframe(
                [{"Materia": k, "Cantidad de Docentes": v} for k, v in materias_conteo.items()],
                use_container_width=True
            )

        else:
            st.error("No se pudieron cargar los indicadores desde la API.")

    except requests.exceptions.ConnectionError:
        st.error("❌ No se pudo conectar con FastAPI.")


# ==============================================================================
# SECCIÓN 4: 🤖 ANÁLISIS DE CV CON IA (Procesamiento, Ollama e Historial)
# ==============================================================================
elif opcion == "🤖 Análisis de CV con IA":
    st.header("🤖 Procesamiento y Análisis Curricular con IA")
    st.markdown("""
    Esta funcionalidad utiliza el modelo de lenguaje local **LLaMA 3** (ejecutado con Ollama)
    para analizar perfiles o currículums de docentes, extrayendo habilidades técnicas, títulos destacados
    y una evaluación de pertinencia para la cátedra universitaria.
    """)

    # Obtenemos la lista de docentes para permitir asociar la evaluación a uno de ellos
    lista_docentes = []
    try:
        r_docs = requests.get(f"{API_URL}/docentes", timeout=5)
        if r_docs.status_code == 200:
            lista_docentes = r_docs.json()
    except requests.exceptions.RequestException:
        pass

    opciones_doc = ["(Ninguno - Evaluación independiente / nuevo postulante)"] + [
        f"#{d['id']} - {d['nombre']} ({d['materia']})" for d in lista_docentes
    ]
    docente_seleccionado = st.selectbox("Asociar análisis a un docente existente (Opcional):", opciones_doc)

    docente_id_elegido = None
    if docente_seleccionado and not docente_seleccionado.startswith("(Ninguno"):
        docente_id_elegido = int(docente_seleccionado.split(" - ")[0].replace("#", ""))

    cv_input = st.text_area(
        "Pega aquí el texto del Currículum o Perfil a evaluar:",
        height=180,
        placeholder="Ej: Licenciada en Ciencias de la Computación (UBA). 8 años de experiencia docente en Algoritmos y Estructuras de Datos, desarrollo backend con Python, FastAPI y bases de datos relacionales..."
    )

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        procesar_click = st.button("🚀 Analizar con IA")

    if procesar_click:
        if not cv_input.strip():
            st.warning("⚠️ Por favor pega algún texto curricular para analizar.")
        else:
            with st.spinner("⏳ Conectando con la API y procesando análisis curricular..."):
                try:
                    payload = {
                        "cv_texto": cv_input.strip(),
                        "docente_id": docente_id_elegido
                    }
                    respuesta = requests.post(f"{API_URL}/procesar-cv-ia", json=payload, timeout=60)

                    if respuesta.status_code == 200:
                        resultado = respuesta.json()
                        resumen = resultado.get("resumen_procesado", "Sin respuesta.")
                        es_sim = resultado.get("es_simulado", False)
                        
                        st.success("✅ ¡Análisis completado y guardado en la base de datos!")
                        st.markdown("### 📋 Dictamen de la Inteligencia Artificial:")
                        st.info(resumen)
                        
                        if not es_sim:
                            st.caption("🟢 Procesado en vivo mediante **LLaMA 3** local.")
                        else:
                            st.caption("ℹ️ Ejecutado en modo contingencia asistida (Ollama no estaba abierto en segundo plano).")
                    else:
                        st.error(f"❌ Error en la API al procesar con IA (Código {respuesta.status_code}).")
                except requests.exceptions.ConnectionError:
                    st.error("❌ No se pudo conectar con la API de FastAPI. Verifica que esté iniciada.")
                except requests.exceptions.Timeout:
                    st.error("⏳ El modelo de IA tardó más de 60 segundos en responder.")

    st.divider()

    # Historial de evaluaciones persistidas en SQLite
    st.subheader("📜 Historial de Evaluaciones con IA Realizadas")
    st.markdown("Todas las evaluaciones generadas por la IA quedan guardadas en la tabla `historial_evaluaciones` de la base de datos.")

    try:
        res_hist = requests.get(f"{API_URL}/evaluaciones", timeout=5)
        if res_hist.status_code == 200:
            historial = res_hist.json()
            if not historial:
                st.info("No hay evaluaciones registradas en el historial.")
            else:
                for h in historial:
                    eval_id = h.get("id")
                    doc_nombre = h.get("docente_nombre") or "Postulante independiente"
                    materia_h = f" — Cátedra: {h.get('materia')}" if h.get("materia") else ""
                    fecha_h = h.get("fecha_evaluacion", "")
                    
                    with st.expander(f"📄 Evaluación #{eval_id}: {doc_nombre}{materia_h} ({fecha_h})"):
                        st.markdown("**Texto original del CV evaluado:**")
                        st.code(h.get("cv_texto_original", ""), language="text")
                        st.markdown("**Devolución de la IA:**")
                        st.write(h.get("resumen_ia", ""))

                        col_espacio, col_eliminar = st.columns([3, 1])
                        with col_eliminar:
                            if st.button("🗑️ Eliminar Evaluación", key=f"btn_del_eval_{eval_id}"):
                                try:
                                    r_del_eval = requests.delete(f"{API_URL}/evaluaciones/{eval_id}", timeout=5)
                                    if r_del_eval.status_code == 200:
                                        st.success(f"Evaluación #{eval_id} eliminada.")
                                        st.rerun()
                                    else:
                                        st.error(f"No se pudo eliminar la evaluación (Código {r_del_eval.status_code}).")
                                except requests.exceptions.RequestException:
                                    st.error("Error al conectar con la API para eliminar.")
        else:
            st.warning("No se pudo obtener el historial de evaluaciones.")
    except requests.exceptions.RequestException:
        st.warning("Conectando con el historial de evaluaciones...")
