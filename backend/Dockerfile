# Imagen de la API FastAPI. Se construye desde la raíz del proyecto (ver docker/compose.yaml).
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend/ /app/backend/

# La base SQLite vive en /app/data, montada como volumen para que persista.
RUN mkdir -p /app/data
EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
