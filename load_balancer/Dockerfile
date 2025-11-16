# =================================================================
# DOCKERFILE PARA EL BALANCEADOR DE CARGA
# =================================================================
# Este Dockerfile construye la imagen para el servicio de balanceo de carga.
# Utiliza una imagen base de Python, instala las dependencias y ejecuta la aplicación.
# =================================================================

# --- Etapa de Construcción ---
# Usamos una imagen oficial de Python como base.
# La versión 'slim' es más ligera que la completa.
FROM python:3.9-slim

# --- Configuración del Entorno ---
# Establece el directorio de trabajo dentro del contenedor.
WORKDIR /app

# --- Instalación de Dependencias ---
# Copia el archivo de requerimientos primero para aprovechar el cache de Docker.
# Si este archivo no cambia, Docker no volverá a instalar las dependencias.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copia del Código Fuente ---
# Copia el resto del código de la aplicación al directorio de trabajo.
COPY . .

# --- Comando de Ejecución ---
# Expone el puerto 80, que es el puerto estándar para HTTP.
EXPOSE 80
# Comando para iniciar la aplicación usando uvicorn, un servidor ASGI rápido.
# Escucha en todas las interfaces (0.0.0.0) en el puerto 80.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
