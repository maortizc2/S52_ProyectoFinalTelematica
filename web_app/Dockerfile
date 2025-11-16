# =================================================================
# DOCKERFILE PARA LA APLICACIÓN WEB (FLASK)
# =================================================================
# Construye la imagen para los servicios de servidores web (inglés y español).
# =================================================================

# --- Etapa de Construcción ---
# Usamos una imagen oficial de Python.
FROM python:3.9-slim

# --- Configuración del Entorno ---
# Crea y establece el directorio de trabajo.
WORKDIR /app

# --- Instalación de Dependencias ---
# Instala curl, necesario para el healthcheck de Docker Compose.
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
# Copia solo el archivo de requerimientos para optimizar el cache de capas de Docker.
COPY requirements.txt .
# Instala las dependencias de Python.
RUN pip install --no-cache-dir -r requirements.txt

# --- Copia del Código Fuente ---
# Copia todo el código de la aplicación al contenedor.
COPY . .

# --- Variables de Entorno ---
# El puerto en el que Gunicorn escuchará. Debe coincidir con el PORT en app.py
# y con el puerto al que apunta el balanceador de carga.
ENV PORT=8000
EXPOSE 8000

# --- Comando de Ejecución ---
# Inicia la aplicación Flask usando Gunicorn, un servidor WSGI de producción.
# -w 4: Inicia 4 'worker processes'. Un buen punto de partida es (2 * num_cores) + 1.
# -b 0.0.0.0:$PORT: Escucha en todas las interfaces en el puerto definido por la variable de entorno.
# app:app: Le dice a Gunicorn que busque el objeto 'app' en el archivo 'app.py'.
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:8000", "--log-level", "debug", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
