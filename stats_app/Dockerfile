# ---- Build Stage ----
# Etapa para instalar dependencias del sistema y de Python
FROM python:3.9-slim as builder

# Instalar dependencias del sistema necesarias para matplotlib
# - build-essential: para compilar paquetes
# - libpq-dev: para psycopg2
# - libfreetype6-dev, libpng-dev: para matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libfreetype6-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

# Instalar dependencias de Python
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


# ---- Final Stage ----
# Etapa final con un entorno de ejecución limpio
FROM python:3.9-slim

# Instalar solo las dependencias de sistema necesarias para la ejecución
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
USER appuser

# Copiar dependencias pre-compiladas
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copiar el código de la aplicación
COPY . .

# Exponer puerto
EXPOSE 8000

# Comando para ejecutar con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1