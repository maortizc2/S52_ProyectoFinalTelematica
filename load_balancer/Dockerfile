# ---- Build Stage ----
FROM python:3.9-slim as builder

WORKDIR /usr/src/app

# Instalar dependencias
COPY requirements.txt ./
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


# ---- Final Stage ----
FROM python:3.9-slim

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

# Exponer el puerto 80, el puerto estándar para HTTP
EXPOSE 80

# Comando para ejecutar con Uvicorn
# Uvicorn es un servidor ASGI de alto rendimiento, ideal para FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/ || exit 1