# Imagen base ligera con Python 3.11
FROM python:3.11-slim

# Variables de entorno para optimizar Python en contenedores
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencias del sistema necesarias para compilar y healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar definicion de dependencias primero para aprovechar cache de capas Docker
COPY pyproject.toml ./

# Instalar dependencias del proyecto
RUN pip install --upgrade pip && \
    pip install .

# Copiar codigo fuente del backend y seeder
COPY app/ ./app/
COPY seeder/ ./seeder/

# Puerto expuesto por FastAPI
EXPOSE 8000

# Healthcheck para verificar que la API responde
HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Comando por defecto para iniciar FastAPI con Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
