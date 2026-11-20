# Bitácora de uso de IA

Usamos IA de dos formas en el trabajo: como **herramienta para desarrollar** (asistentes de código) y como **parte del sistema** (Ollama, para analizar CVs y armar informes). Acá contamos cómo nos ayudó, qué decidimos y en qué nos tuvimos que frenar a corregir.

## Herramientas que usamos

| Herramienta | Para qué |
|---|---|
| Claude (Anthropic) | Backend: diseñar la estructura de la API, escribir endpoints y tests, integrar el frontend con la API y armar los workflows de n8n |
| Ollama + llama3 | La IA del sistema: corre local en la PC, analiza los CVs y redacta el informe de la planta |
| *(completar)* | *(herramientas que usaron los demás para la base de datos, el frontend y n8n)* |

## Decisiones técnicas

**Ollama en vez de una API paga.** La consigna pedía algo gratis, y además los CVs tienen datos personales. Con Ollama todo queda en la PC y no se manda nada afuera. La contra es que es más lento sin GPU, así que le pusimos un tiempo máximo de espera configurable.

**Separar lo que calcula Python de lo que dice la IA.** Los indicadores, las alertas y el puntaje de compatibilidad entre CV y materia salen de reglas que se pueden explicar número por número. La IA solo resume el CV y redacta el informe. Incluso el informe lo arma con números que le pasa Python, para que no invente datos.

**No confiar a ciegas en la IA.** Le pedimos la respuesta en JSON y la validamos. Si la estructura viene mal, se reintenta una vez y, si sigue mal, se devuelve un error. Las materias que sugiere se comparan con el catálogo real, y si inventa alguna se descarta y queda una advertencia.

**Una persona aprueba antes de guardar.** El endpoint que analiza el CV no guarda nada. En n8n, si el análisis trae advertencias, no se guarda y queda pendiente de revisión.

**Ordenar el backend en módulos.** Al principio era todo un único `main.py`. Lo separamos en configuración, validación (schemas), reglas, IA, manejo de errores y routers, así cada parte se entiende por separado.

## Dificultades y cómo las resolvimos

- **Conflicto de merge.** El frontend y el backend tocaron `main.py` al mismo tiempo y Git marcó conflicto. Nos quedamos con la estructura nueva y pasamos los endpoints que usaba el frontend (`PUT /docentes`, `DELETE /evaluaciones`) para no romperlo.
- **`requirements.txt` ilegible.** Se había generado desde PowerShell y quedó guardado en UTF-16, y pip en Docker no lo leía bien. Lo pasamos a UTF-8.
- **El puntaje por reglas daba cualquier cosa.** Primero castigaba a las materias de nombre largo: "Elementos de Programación IA y LowCode" daba 0 aunque el CV hablara de LLMs y n8n. Después apareció un falso positivo más gracioso: la palabra "ingenier**ía**" contaba como "IA". Lo corregimos contando por concepto y pidiendo coincidencia exacta para las siglas cortas.
- **El modo contingencia mentía.** Cuando Ollama estaba apagado, el sistema devolvía siempre "perfil altamente compatible, se recomienda su incorporación", sin importar el CV, y lo guardaba como si fuera un análisis real. Lo cambiamos para que muestre el cálculo real por reglas y aclare que no hubo IA. Además encontramos que ese texto pisaba el perfil del docente, y lo arreglamos.
- **Workflows de n8n incompletos.** Ninguno tenía condición, y el de CV le mandaba a Ollama un texto fijo en vez de pasar por la API. Los rehicimos para que los tres usen la API y tengan su nodo IF.
- **JSON roto en el webhook.** El cuerpo del request se armaba pegando texto, así que un nombre con comillas o un salto de línea lo rompía. Ahora se arma con `JSON.stringify`.
- **Ollama no se veía desde Docker.** Por defecto escucha solo en `127.0.0.1`. Si la API corre en un contenedor, hay que iniciarlo con `OLLAMA_HOST=0.0.0.0`.

## Cómo verificamos que todo anda

- **Tests automáticos** con pytest (22). Cubren el CRUD, los errores (404, 409, 422), los indicadores y alertas, la IA simulada respondiendo bien, con basura o apagada, y las llamadas exactas que hace el frontend.
- **Workflows de n8n** importados y ejecutados por todas las ramas de cada condición: alta correcta, email duplicado, datos inválidos, IA con y sin advertencias, Ollama apagado, con y sin alertas altas.
- **Prueba integrada** a mano, con Ollama real en la PC, la API, Streamlit y n8n funcionando juntos.

## Lo que nos llevamos

La IA acelera muchísimo, pero varias veces propuso cosas que andaban "a medias", y nos dimos cuenta recién al probarlas. Los errores del scoring y del modo contingencia los encontramos así. Probar cada cambio y entender el código antes de subirlo fue lo que más nos sirvió.
