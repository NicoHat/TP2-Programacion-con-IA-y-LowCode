import streamlit as st
import requests

# URL base de tu FastAPI
API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Gestión de Planta Docente", layout="wide")

st.title("🎓 Sistema Inteligente de Gestión de Planta Docente")
st.markdown("Plataforma para el registro, consulta y análisis de recursos humanos académicos.")

# Pestañas principales de la interfaz
pestana_gestion, pestana_ia = st.tabs(["📚 Gestión de Docentes", "🤖 Análisis de CV con IA"])

with pestana_gestion:
    st.header("Registro y Consulta de Docentes")
    
    # Formulario de alta
    with st.form("form_docente"):
        st.subheader("Agregar Nuevo Docente")
        nombre = st.text_input("Nombre completo")
        email = st.text_input("Correo electrónico")
        materia = st.text_input("Materia asignada")
        dedicacion = st.selectbox("Dedicación", ["Simple", "Semi-exclusiva", "Exclusiva"])
        cv_resumen = st.text_area("Breve descripción del perfil o antecedentes")
        
        submitted = st.form_submit_button("Guardar Docente")
        
        if submitted:
            if nombre and email and materia:
                payload = {
                    "nombre": nombre,
                    "email": email,
                    "materia": materia,
                    "dedicacion": dedicacion,
                    "cv_resumen": cv_resumen
                }
                try:
                    response = requests.post(f"{API_URL}/docentes", json=payload)
                    if response.status_code == 200:
                        st.success("¡Docente registrado con éxito!")
                    else:
                        st.error("Error al registrar en la API.")
                except requests.exceptions.ConnectionError:
                    st.error("No se pudo conectar con el servidor de FastAPI. ¿Está encendido?")
            else:
                st.warning("Por favor completa al menos nombre, email y materia.")

    st.divider()
    
    # Listado de docentes actuales
    st.subheader("Listado de Planta Docente Actual")
    try:
        res = requests.get(f"{API_URL}/docentes")
        if res.status_code == 200:
            docentes = res.json()
            if docentes:
                for doc in docentes:
                    with st.expander(f"👨‍🏫 {doc['nombre']} - {doc['materia']} ({doc['dedicacion']})"):
                        st.write(f"**Email:** {doc['email']}")
                        st.write(f"**Perfil:** {doc['cv_resumen']}")
            else:
                st.info("No hay docentes registrados todavía.")
    except:
        st.warning("Conectando con la API...")

with pestana_ia:
    st.header("Procesamiento de Perfiles con Inteligencia Artificial")
    st.markdown("Pega el texto de un currículum o perfil para extraer las competencias automáticamente mediante IA local.")
    
    cv_texto_input = st.text_area("Texto del Currículum / Perfil Docente:")
    
    if st.button("Procesar con IA"):
        if cv_texto_input:
            try:
                response = requests.post(f"{API_URL}/procesar-cv-ia", json={"cv_texto": cv_texto_input})
                if response.status_code == 200:
                    resultado = response.json()
                    st.success("¡Análisis completado!")
                    st.info(resultado.get("resumen_procesado"))
                else:
                    st.error("Error al procesar con la API.")
            except requests.exceptions.ConnectionError:
                st.error("Error de conexión con FastAPI.")
        else:
            st.warning("Ingresa algún texto de prueba para analizar.")