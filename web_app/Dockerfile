# ---- Build Stage ----
# Etapa para construir dependencias, si fuera necesario.
# Usamos una imagen completa para tener herramientas de compilación.
FROM python:3.9-slim as builder

WORKDIR /usr/src/app

# Instalar dependencias para no reinstalarlas en cada cambio de código
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


# ---- Final Stage ----
# Etapa final con el entorno de ejecución limpio.
FROM python:3.9-slim

# Crear un usuario no-root para mayor seguridad
RUN useradd --create-home appuser
WORKDIR /home/appuser/app
USER appuser

# Copiar las dependencias pre-compiladas de la etapa anterior
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/*

# Copiar el código de la aplicación
COPY . .

# Exponer el puerto que Gunicorn usará
EXPOSE 8000

# Comando para ejecutar la aplicación con Gunicorn
# --bind 0.0.0.0:8000 -> Escucha en todas las interfaces en el puerto 8000
# --workers 4 -> Número de procesos de trabajo (ajustar según los cores de la VM)
# app:app -> Busca el objeto 'app' en el archivo 'app.py'
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "app:app"]

# Healthcheck para que Docker Swarm sepa si el contenedor está saludable
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/ || exit 1