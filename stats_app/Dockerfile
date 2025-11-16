# =================================================================
# DOCKERFILE PARA LA APLICACIÓN DE ESTADÍSTICAS
# =================================================================
# Construye la imagen para el servicio de estadísticas.
# Instala dependencias de sistema necesarias para Matplotlib.
# =================================================================

# --- Etapa de Construcción ---
# Usamos una imagen completa de Python sobre Debian (no 'slim') para tener 'apt'.
FROM python:3.9

# --- Instalación de Dependencias de Sistema ---
# Matplotlib en un entorno 'headless' (sin interfaz gráfica) como Docker
# requiere algunas librerías de sistema para renderizar gráficos.
# - build-essential: Contiene compiladores y herramientas de desarrollo.
# - libgl1-mesa-glx: Es una librería de renderizado de gráficos 3D.
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# --- Configuración del Entorno ---
WORKDIR /app

# --- Instalación de Dependencias de Python ---
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- Copia del Código Fuente ---
COPY . .

# --- Comando de Ejecución ---
# Expone el puerto 5000, donde correrá la aplicación Flask.
EXPOSE 5000
# Inicia la aplicación usando Gunicorn.
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:5000", "app:app"]
