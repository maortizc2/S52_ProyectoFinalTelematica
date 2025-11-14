# Guía Completa de Despliegue: De Local a Producción en AWS

Este documento es la guía definitiva para configurar, desplegar y mantener el proyecto. Contiene todos los pasos, archivos y comandos necesarios.

## Paso 0 — Preparación y Análisis Local

*   **Objetivo:** Entender la estructura del proyecto y preparar el entorno para las modificaciones.
*   **Explicación:** Se ha realizado un análisis completo del código y la configuración existentes. Se detectaron archivos vacíos, configuraciones inseguras y código no optimizado para producción. Los siguientes pasos corregirán y completarán el proyecto.
*   **Checks automáticos (a ejecutar en tu máquina local):**
    *   **Listar archivos:** `ls -R` (o `dir /s` en Windows) para ver la estructura.
    *   **Verificar dependencias:** `pip freeze` dentro de un virtualenv para cada servicio.
    *   **Análisis estático (opcional, recomendado):** `pylint web_app/ stats_app/ load_balancer/` para detectar errores y malas prácticas en Python.

## Paso 1 — Corrección y Mejora del Código Fuente

*   **Objetivo:** Refactorizar las aplicaciones para que sean robustas, seguras y configurables mediante variables de entorno y secretos.
*   **Explicación:** Se han modificado las 3 aplicaciones (`web_app`, `stats_app`, `load_balancer`) para:
    1.  Leer credenciales de la base de datos de forma segura desde secretos de Docker (`/run/secrets/db_pass`) o variables de entorno.
    2.  Añadir endpoints de `healthcheck` (`/healthz`) para que el orquestador pueda verificar su estado.
    3.  Mejorar la validación de datos y el logging.
    4.  Preparar `stats_app` para usar AWS SES además de SMTP.
    5.  Hacer el `load_balancer` más resiliente con health checks activos y un mejor manejo de fallos.
*   **Archivos Corregidos:** Los siguientes archivos han sido actualizados en tu repositorio.

### `web_app/app.py` (mejorado)
```python
from flask import Flask, request, render_template, redirect, url_for, jsonify
import os
import psycopg2
import datetime
from psycopg2.extras import RealDictCursor
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- Configuración ---
LANG = os.getenv("LANG", "en")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")

def get_db_password():
    """Obtiene la contraseña de la BD desde un secret de Docker o una variable de entorno."""
    if os.path.exists('/run/secrets/db_pass'):
        with open('/run/secrets/db_pass', 'r') as secret_file:
            return secret_file.read().strip()
    return os.getenv("DB_PASS", "apppass")

DB_PASS = get_db_password()

def get_conn():
    """Establece y retorna una conexión a la base de datos."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Error al conectar a la base de datos: {e}")
        return None

@app.route("/")
def index():
    """Renderiza la página principal con el formulario de registro."""
    title = "User Registration" if LANG.startswith("en") else "Registro de Usuarios"
    return render_template("index.html", title=title, lang=LANG)

@app.route("/register", methods=["POST"])
def register():
    """Maneja el registro de usuarios desde el formulario HTML."""
    name = request.form.get("name")
    comuna = request.form.get("comuna")
    carrera = request.form.get("carrera")

    if not all([name, comuna, carrera]):
        return "Error: Todos los campos son requeridos.", 400

    try:
        comuna_int = int(comuna)
        if not 1 <= comuna_int <= 10:
            raise ValueError("Comuna debe estar entre 1 y 10.")
    except (ValueError, TypeError):
        return "Error: 'comuna' debe ser un número entre 1 y 10.", 400

    fecha = datetime.datetime.utcnow()
    conn = get_conn()
    if not conn:
        return "Error: No se pudo conectar a la base de datos.", 500

    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (name, comuna, date, carrera, lang) VALUES (%s, %s, %s, %s, %s)",
                (name, comuna_int, fecha, carrera, LANG)
            )
            conn.commit()
        logging.info(f"Usuario '{name}' registrado desde lang='{LANG}'.")
    except psycopg2.Error as e:
        logging.error(f"Error al insertar en la base de datos: {e}")
        return "Error: Falla al registrar el usuario.", 500
    finally:
        if conn:
            conn.close()

    return redirect(url_for("index"))

@app.route("/api/register", methods=["POST"])
def api_register():
    """Maneja el registro de usuarios desde la API."""
    data = request.json
    name = data.get("name")
    comuna = data.get("comuna")
    carrera = data.get("carrera")

    if not all([name, comuna, carrera]):
        return jsonify({"error": "Todos los campos son requeridos."}), 400

    try:
        comuna_int = int(comuna)
        if not 1 <= comuna_int <= 10:
            raise ValueError("Comuna debe estar entre 1 y 10.")
    except (ValueError, TypeError):
        return jsonify({"error": "'comuna' debe ser un número entre 1 y 10."}), 400

    fecha = datetime.datetime.utcnow()
    conn = get_conn()
    if not conn:
        return jsonify({"error": "No se pudo conectar a la base de datos."}), 500

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO users (name, comuna, date, carrera, lang) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (name, comuna_int, fecha, carrera, LANG)
            )
            new_id = cur.fetchone()["id"]
            conn.commit()
        logging.info(f"Usuario '{name}' registrado vía API desde lang='{LANG}'. ID: {new_id}")
        return jsonify({"id": new_id, "status": "ok"}), 201
    except psycopg2.Error as e:
        logging.error(f"Error de API al insertar en la base de datos: {e}")
        return jsonify({"error": "Falla al registrar el usuario."}), 500
    finally:
        if conn:
            conn.close()

@app.route("/healthz")
def healthz():
    """Verifica la salud del servicio, incluyendo la conexión a la BD."""
    conn = get_conn()
    if conn:
        conn.close()
        return jsonify({"status": "ok", "db_connection": "ok"}), 200
    else:
        return jsonify({"status": "error", "db_connection": "failed"}), 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```

### `stats_app/app.py` (mejorado)
```python
from flask import Flask, request, jsonify
import os
import io
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import psycopg2
import smtplib
import boto3
from botocore.exceptions import ClientError
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# --- Configuración ---
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "adminpass")

# Configuración del modo de email: 'smtp' (Mailtrap) o 'ses' (AWS)
EMAIL_MODE = os.getenv("EMAIL_MODE", "smtp")
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@yourdomain.com")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

def get_secret(secret_name, default=None):
    """Obtiene un secret desde un archivo de Docker o una variable de entorno."""
    path = f'/run/secrets/{secret_name}'
    if os.path.exists(path):
        with open(path, 'r') as secret_file:
            return secret_file.read().strip()
    return os.getenv(secret_name.upper(), default)

DB_PASS = get_secret("db_pass", "apppass")
SMTP_SERVER = get_secret("smtp_server", "smtp.mailtrap.io")
SMTP_PORT = int(get_secret("smtp_port", 587))
SMTP_USER = get_secret("smtp_user")
SMTP_PASS = get_secret("smtp_pass")

def get_conn():
    """Establece y retorna una conexión a la base de datos."""
    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
        return conn
    except psycopg2.OperationalError as e:
        logging.error(f"Error al conectar a la base de datos: {e}")
        return None

def check_auth(u, p):
    """Verifica las credenciales de administrador."""
    return u == ADMIN_USER and p == ADMIN_PASS

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return ('Unauthorized', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
        return f(*args, **kwargs)
    return decorated

def fetch_data():
    """Obtiene los datos de usuarios de la BD y los retorna como un DataFrame."""
    conn = get_conn()
    if not conn:
        raise ConnectionError("No se pudo conectar a la base de datos.")
    try:
        query = "SELECT name, comuna, date, carrera, lang FROM users"
        df = pd.read_sql(query, conn, parse_dates=["date"])
        return df
    finally:
        if conn:
            conn.close()

def build_plots_pdf(df):
    """Genera un PDF con múltiples gráficas a partir de un DataFrame."""
    pdf_buf = io.BytesIO()
    with PdfPages(pdf_buf) as pdf:
        # Gráfica 1: Registros por carrera
        fig1 = plt.figure(figsize=(10, 6))
        df['carrera'].value_counts().plot(kind='bar', title='Registros por Carrera')
        plt.ylabel('Cantidad')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        pdf.savefig(fig1)
        plt.close(fig1)

        # Gráfica 2: Registros por comuna
        fig2 = plt.figure(figsize=(10, 6))
        df['comuna'].value_counts().sort_index().plot(kind='bar', title='Registros por Comuna')
        plt.ylabel('Cantidad')
        plt.xlabel('Comuna')
        plt.xticks(rotation=0)
        plt.tight_layout()
        pdf.savefig(fig2)
        plt.close(fig2)

        # Gráfica 3: Registros a lo largo del tiempo
        fig3 = plt.figure(figsize=(10, 6))
        df.set_index('date').resample('D').size().plot(title='Registros por Día')
        plt.ylabel('Cantidad')
        plt.xlabel('Fecha')
        plt.tight_layout()
        pdf.savefig(fig3)
        plt.close(fig3)
    
    pdf_buf.seek(0)
    return pdf_buf

def send_email_smtp(to_email, subject, body, attachment_buf):
    """Envía un email usando SMTP (Mailtrap)."""
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'plain'))

    part = MIMEApplication(attachment_buf.read(), Name="stats_report.pdf")
    part['Content-Disposition'] = 'attachment; filename="stats_report.pdf"'
    msg.attach(part)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.starttls()
        if SMTP_USER and SMTP_PASS:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)
    logging.info(f"Email enviado a {to_email} vía SMTP.")

def send_email_ses(to_email, subject, body, attachment_buf):
    """Envía un email usando AWS SES."""
    client = boto3.client('ses', region_name=AWS_REGION)
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'plain'))

    part = MIMEApplication(attachment_buf.read(), Name="stats_report.pdf")
    part['Content-Disposition'] = 'attachment; filename="stats_report.pdf"'
    msg.attach(part)

    try:
        response = client.send_raw_email(
            Source=EMAIL_FROM,
            Destinations=[to_email],
            RawMessage={'Data': msg.as_string()}
        )
        logging.info(f"Email enviado a {to_email} vía SES. Message ID: {response['MessageId']}")
    except ClientError as e:
        logging.error(f"Error al enviar email con SES: {e.response['Error']['Message']}")
        raise

@app.route("/admin/send-stats", methods=["POST"])
@requires_auth
def send_stats():
    """Endpoint para generar y enviar el informe de estadísticas."""
    to_email = request.json.get("to", "ialondonoo@eafit.edu.co")
    
    try:
        df = fetch_data()
        if df.empty:
            return jsonify({"status": "aborted", "reason": "No data available to generate stats."} ), 404
        
        pdf_buf = build_plots_pdf(df)
        
        subject = f"Informe de Estadísticas - {datetime.date.today()}"
        body = "Adjunto encontrarás el informe de estadísticas de usuarios."

        if EMAIL_MODE == 'ses':
            send_email_ses(to_email, subject, body, pdf_buf)
        else: # 'smtp' por defecto
            send_email_smtp(to_email, subject, body, pdf_buf)
            
        return jsonify({"status": "sent", "to": to_email, "mode": EMAIL_MODE})

    except ConnectionError as e:
        return jsonify({"error": str(e)}), 503
    except Exception as e:
        logging.error(f"Error inesperado en /admin/send-stats: {e}")
        return jsonify({"error": "Ocurrió un error interno al procesar la solicitud."} ), 500

@app.route("/healthz")
def healthz():
    """Verifica la salud del servicio."""
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010, debug=True)
```

### `load_balancer/main.py` (mejorado)
```python
from fastapi import FastAPI, Request, Response, HTTPException
import httpx
import os
import asyncio
import logging
from collections import deque
from typing import Deque, Dict, List

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI(title="Load Balancer")

# --- Configuración ---
BACKENDS_STR = os.getenv("BACKENDS", "http://localhost:5001,http://localhost:5002")
BACKENDS: List[str] = [b.strip() for b in BACKENDS_STR.split(",")]
backend_deque: Deque[str] = deque(BACKENDS)

# Diccionario para rastrear el estado de salud y el tiempo de la última falla
health_status: Dict[str, bool] = {backend: True for backend in BACKENDS}
last_failure: Dict[str, float] = {backend: 0.0 for backend in BACKENDS}

# --- Constantes de reintento y salud ---
TIMEOUT = float(os.getenv("BACKEND_TIMEOUT", 5.0))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", 3))
RETRY_BACKOFF = float(os.getenv("RETRY_BACKOFF", 0.5)) # Base para el backoff exponencial
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", 10)) # Segundos
FAILURE_THRESHOLD = int(os.getenv("FAILURE_THRESHOLD", 3)) # Fallos para marcar como 'down'
COOLDOWN_PERIOD = int(os.getenv("COOLDOWN_PERIOD", 30)) # Segundos antes de reintentar un backend 'down'

# Contadores de fallos
failure_counters: Dict[str, int] = {backend: 0 for backend in BACKENDS}

async def health_checker():
    """Tarea en segundo plano que verifica la salud de los backends periódicamente."""
    async with httpx.AsyncClient() as client:
        while True:
            for backend in BACKENDS:
                try:
                    # Usamos el endpoint /healthz de las web apps
                    resp = await client.get(f"{backend}/healthz", timeout=2.0)
                    if resp.status_code == 200:
                        if not health_status[backend]:
                            logging.info(f"Backend {backend} está de vuelta. Marcando como 'UP'.")
                            health_status[backend] = True
                            failure_counters[backend] = 0
                    else:
                        handle_failure(backend)
                except httpx.RequestError:
                    handle_failure(backend)
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)

def handle_failure(backend: str):
    """Maneja la lógica de fallo de un backend."""
    if health_status[backend]: # Solo actuar si estaba previamente 'UP'
        failure_counters[backend] += 1
        if failure_counters[backend] >= FAILURE_THRESHOLD:
            health_status[backend] = False
            last_failure[backend] = asyncio.get_event_loop().time()
            logging.warning(f"Backend {backend} ha fallado {FAILURE_THRESHOLD} veces. Marcando como 'DOWN'.")

async def proxy_request(client: httpx.AsyncClient, backend: str, request: Request) -> httpx.Response:
    """Redirige una petición a un backend específico."""
    url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
    headers = dict(request.headers)
    # El host debe coincidir con el del backend para evitar problemas de enrutamiento
    headers["host"] = httpx.URL(backend).host
    
    req = client.build_request(
        method=request.method,
        url=url,
        headers=headers,
        content=await request.body(),
        timeout=TIMEOUT,
    )
    
    # Base URL del backend
    base_url = httpx.URL(backend)
    
    # Realizar la petición
    resp = await client.send(req, base_url=base_url)
    return resp

@app.on_event("startup")
async def startup_event():
    """Inicia las tareas en segundo plano al arrancar la aplicación."""
    asyncio.create_task(health_checker())
    logging.info("Load Balancer iniciado.")
    logging.info(f"Backends configurados: {BACKENDS}")

@app.api_route("/{path:path}")
async def round_robin_proxy(request: Request, path: str):
    """Middleware principal que implementa el proxy con Round-Robin y reintentos."""
    async with httpx.AsyncClient() as client:
        # Intentar en todos los backends disponibles
        for _ in range(len(backend_deque)):
            backend = backend_deque[0]
            backend_deque.rotate(-1) # Rotar para la siguiente petición

            # Si el backend está marcado como 'DOWN', verificar si ha pasado el cooldown
            if not health_status[backend]:
                now = asyncio.get_event_loop().time()
                if now - last_failure[backend] < COOLDOWN_PERIOD:
                    continue # Saltar este backend, aún en cooldown

            # Intentar conectar con el backend con lógica de reintento y backoff
            last_exc = None
            for attempt in range(MAX_RETRIES):
                try:
                    logging.info(f"Intentando redirigir {request.method} {request.url.path} a {backend} (intento {attempt + 1})")
                    resp = await proxy_request(client, backend, request)
                    
                    # Si el backend responde con 5xx, considerarlo un fallo y reintentar
                    if resp.status_code >= 500:
                        raise httpx.HTTPStatusError(f"El servidor backend respondió con {resp.status_code}", request=resp.request, response=resp)

                    # Éxito: devolver la respuesta al cliente
                    # Añadir una cabecera para identificar qué backend respondió
                    headers = dict(resp.headers)
                    headers["X-Backend-Served-By"] = backend
                    return Response(content=resp.content, status_code=resp.status_code, headers=headers)

                except Exception as e:
                    last_exc = e
                    logging.warning(f"Fallo al contactar {backend}: {e}")
                    # Backoff exponencial antes del siguiente reintento
                    await asyncio.sleep(RETRY_BACKOFF * (2 ** attempt))
            
            # Si todos los reintentos para este backend fallaron, marcarlo como 'DOWN'
            handle_failure(backend)

    # Si se llega aquí, todos los backends han fallado
    logging.error("Todos los backends han fallado. No se puede servir la petición.")
    raise HTTPException(status_code=503, detail="Service Unavailable: All backends are down.")

@app.get("/lb/healthz", include_in_schema=False)
def lb_healthz():
    """Endpoint de salud del propio balanceador."""
    return {"status": "ok"}

@app.get("/lb/metrics", include_in_schema=False)
def metrics():
    """Endpoint de métricas que muestra el estado de los backends."""
    return {
        "backends": BACKENDS,
        "health_status": health_status,
        "failure_counters": failure_counters
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### `infra/schema.sql` (creado)
```sql
-- Esquema para la base de datos del proyecto
-- Este script se puede ejecutar para inicializar la estructura de la tabla.

-- Eliminar la tabla si ya existe para permitir una reinicialización limpia
DROP TABLE IF EXISTS users;

-- Crear la tabla de usuarios
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    comuna INTEGER NOT NULL CHECK (comuna >= 1 AND comuna <= 10),
    date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    carrera VARCHAR(50) NOT NULL CHECK (carrera IN ('Medicina', 'Ingeniería', 'Abogacía', 'Licenciatura')),
    lang VARCHAR(5) NOT NULL -- 'en' o 'es' para saber qué frontend lo registró
);

-- Opcional: Crear un índice en la columna 'carrera' y 'comuna' para acelerar las consultas de estadísticas
CREATE INDEX idx_users_carrera ON users(carrera);
CREATE INDEX idx_users_comuna ON users(comuna);

-- Mensaje de finalización
\echo "Tabla 'users' creada exitosamente."
```

### `infra/seed_db.py` (creado)
```python
import os
import psycopg2
import random
from datetime import datetime

# --- Configuración ---
# Lee las variables de entorno o usa valores por defecto
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASS = os.getenv("DB_PASS", "apppass")

# Datos de ejemplo
NOMBRES = ["Ana", "Carlos", "Beatriz", "David", "Elena", "Fernando", "Gloria", "Hector"]
CARRERAS = ['Medicina', 'Ingeniería', 'Abogacía', 'Licenciatura']
LANGS = ['en', 'es']
NUM_RECORDS = 50

def seed_data():
    """Inserta datos de ejemplo en la base de datos."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        print("Conexión a la base de datos exitosa.")
    except psycopg2.OperationalError as e:
        print(f"Error: No se pudo conectar a la base de datos.")
        print(f"Detalles: {e}")
        return

    try:
        with conn.cursor() as cur:
            # Verificar si la tabla ya tiene datos
            cur.execute("SELECT COUNT(*) FROM users")
            if cur.fetchone()[0] > 0:
                print("La tabla 'users' ya contiene datos. No se insertarán nuevos registros.")
                return

            print(f"Insertando {NUM_RECORDS} registros de ejemplo...")
            for i in range(NUM_RECORDS):
                name = random.choice(NOMBRES) + f"_{i}"
                comuna = random.randint(1, 10)
                carrera = random.choice(CARRERAS)
                lang = random.choice(LANGS)
                
                cur.execute(
                    "INSERT INTO users (name, comuna, date, carrera, lang) VALUES (%s, %s, %s, %s, %s)",
                    (name, comuna, datetime.utcnow(), carrera, lang)
                )
            
            conn.commit()
            print(f"{NUM_RECORDS} registros insertados exitosamente.")

    except psycopg2.Error as e:
        print(f"Error durante la inserción de datos: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Conexión a la base de datos cerrada.")

if __name__ == "__main__":
    print("Iniciando el script para poblar la base de datos...")
    seed_data()
    print("Script finalizado.")
```

### `stats_app/requirements.txt` (actualizado)
```
Flask==2.3.2
pandas==2.1.1
matplotlib==3.8.1
psycopg2-binary==2.9.7
gunicorn
boto3
```

### `web_app/templates/index.html` (mejorado)
```html
<!doctype html>
<html lang="{{ lang }}">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 40px auto; padding: 0 20px; background-color: #f4f4f9; }
        h1 { color: #0056b3; text-align: center; }
        .container { background: #fff; padding: 20px 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        form { display: flex; flex-direction: column; gap: 15px; }
        label { font-weight: bold; display: flex; flex-direction: column; }
        input, select, button { padding: 10px; border-radius: 5px; border: 1px solid #ccc; font-size: 16px; }
        input:focus, select:focus { border-color: #0056b3; outline: none; }
        button { background-color: #0056b3; color: white; font-weight: bold; border: none; cursor: pointer; transition: background-color 0.2s; }
        button:hover { background-color: #004494; }
        .api-info { margin-top: 30px; padding: 15px; background-color: #e9ecef; border-left: 4px solid #0056b3; font-family: monospace; font-size: 14px; white-space: pre-wrap; word-wrap: break-word; }
        .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>{{ title }}</h1>
        <form action="/register" method="post">
            <label>
                {{ "Name" if lang.startswith("en") else "Nombre" }}:
                <input name="name" required>
            </label>
            <label>
                {{ "District (1-10)" if lang.startswith("en") else "Comuna (1-10)" }}: 
                <input name="comuna" type="number" min="1" max="10" value="1" required>
            </label>
            <label>
                {{ "Major" if lang.startswith("en") else "Carrera" }}:
                <select name="carrera" required>
                    <option value="" disabled selected>{{ "Select an option" if lang.startswith("en") else "Selecciona una opción" }}</option>
                    <option>Medicina</option>
                    <option>Ingeniería</option>
                    <option>Abogacía</option>
                    <option>Licenciatura</option>
                </select>
            </label>
            <button type="submit">{{ "Register" if lang.startswith("en") else "Registrar" }}</button>
        </form>

        <div class="api-info">
            <p><b>{{ "Or use the API" if lang.startswith("en") else "O usa la API" }}:</b></p>
            <code>
POST /api/register
Content-Type: application/json

{
  "name": "API User",
  "comuna": 5,
  "carrera": "Ingeniería"
}
            </code>
        </div>
    </div>
    <div class="footer">
        <p>Served by web server with language: <strong>{{ lang }}</strong></p>
    </div>
</body>
</html>
```

## Paso 2 — Containerización de Servicios (Docker)

*   **Objetivo:** Crear `Dockerfile` optimizados para cada servicio.
*   **Explicación:** Se usarán *multi-stage builds* para crear imágenes ligeras y seguras. La primera etapa (`builder`) instala dependencias, y la segunda (`runtime`) copia solo los artefactos necesarios, reduciendo la superficie de ataque y el tamaño final de la imagen. Se crea un usuario no-root (`appuser`) por seguridad.
*   **Archivos a Crear/Actualizar:**

### `web_app/Dockerfile`
```dockerfile
# ---- Builder Stage ----
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# ---- Runtime Stage ----
FROM python:3.11-slim

WORKDIR /app

# Crear usuario no-root
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

# Copiar dependencias pre-compiladas y código fuente
COPY --from=builder /app/wheels /wheels
COPY . .

# Instalar dependencias desde el caché local
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

# Puerto que expone la aplicación
EXPOSE 5000

# Comando para ejecutar la aplicación con Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "app:app"]
```

### `stats_app/Dockerfile`
```dockerfile
# ---- Builder Stage ----
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependencias del sistema para matplotlib
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev build-essential

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# ---- Runtime Stage ----
FROM python:311-slim

WORKDIR /app

# Instalar dependencias del sistema runtime
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

# Copiar dependencias y código
COPY --from=builder /app/wheels /wheels
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

EXPOSE 5010
CMD ["gunicorn", "--bind", "0.0.0.0:5010", "--workers", "2", "app:app"]
```

### `load_balancer/Dockerfile`
```dockerfile
# ---- Builder Stage ----
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# ---- Runtime Stage ----
FROM python:3.11-slim

WORKDIR /app

# Crear usuario no-root
RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser/app

# Copiar dependencias y código
COPY --from=builder /app/wheels /wheels
COPY . .

# Instalar dependencias
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

## Paso 3 — Orquestación Local (Docker Compose)

*   **Objetivo:** Configurar un entorno de desarrollo local completo con `docker-compose`.
*   **Explicación:** Este archivo `docker-compose.yml` define todos los servicios, redes y volúmenes. Usa `build: .` para construir las imágenes localmente en lugar de descargarlas. Las credenciales se manejan en un archivo `.env` que no debe subirse a Git.
*   **Ruta Corta (Test Local):**

### 1. Crear archivo `.env`
Crea este archivo en la raíz del proyecto.
```env
# Archivo de variables de entorno para desarrollo local
# NO SUBIR A GIT

# Credenciales de la Base de Datos
DB_PASS=supersecretpassword

# Credenciales de Admin para Stats App
ADMIN_USER=admin
ADMIN_PASS=adminsecret

# Credenciales para Mailtrap (pruebas de email)
# Obtener de https://mailtrap.io
SMTP_USER=<TU_USUARIO_MAILTRAP>
SMTP_PASS=<TU_PASSWORD_MAILTRAP>
```

### 2. Crear archivo `docker-compose.yml` (mejorado)
```yaml
version: '3.8'

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD: ${DB_PASS}
    volumes:
      - db_data:/var/lib/postgresql/data
      # Script para inicializar el schema al crear la BD por primera vez
      - ./infra/schema.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - mynet
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U appuser -d appdb"]
      interval: 10s
      timeout: 5s
      retries: 5

  web1:
    build: ./web_app
    environment:
      - LANG=en
      - DB_HOST=db
      - DB_NAME=appdb
      - DB_USER=appuser
      - DB_PASS=${DB_PASS}
      # Para que Gunicorn muestre logs en tiempo real
      - PYTHONUNBUFFERED=1
    depends_on:
      db:
        condition: service_healthy
    networks:
      - mynet

  web2:
    build: ./web_app
    environment:
      - LANG=es
      - DB_HOST=db
      - DB_NAME=appdb
      - DB_USER=appuser
      - DB_PASS=${DB_PASS}
      - PYTHONUNBUFFERED=1
    depends_on:
      db:
        condition: service_healthy
    networks:
      - mynet

  stats:
    build: ./stats_app
    environment:
      - DB_HOST=db
      - DB_NAME=appdb
      - DB_USER=appuser
      - ADMIN_USER=${ADMIN_USER}
      - ADMIN_PASS=${ADMIN_PASS}
      - EMAIL_MODE=smtp
      - SMTP_USER=${SMTP_USER}
      - SMTP_PASS=${SMTP_PASS}
      - PYTHONUNBUFFERED=1
    depends_on:
      db:
        condition: service_healthy
    networks:
      - mynet
    ports:
      - "5010:5010"

  lb:
    build: ./load_balancer
    environment:
      # Los backends apuntan a los servicios web internos en el puerto que exponen
      - BACKENDS=http://web1:5000,http://web2:5000
      - PYTHONUNBUFFERED=1
    ports:
      - "80:8000" # Puerto 80 del host mapeado al 8000 del contenedor
    depends_on:
      - web1
      - web2
    networks:
      - mynet

volumes:
  db_data:

networks:
  mynet:
```

### 3. Comandos de ejecución y verificación
```bash
# Shell: bash/zsh/PowerShell

# 1. Levantar todos los servicios en segundo plano
docker-compose up --build -d

# 2. Verificar que todos los contenedores están corriendo
docker-compose ps

# 3. Poblar la base de datos con datos de ejemplo (opcional)
docker-compose exec db python /app/infra/seed_db.py  # Asumiendo que montas el script

# 4. Verificar el balanceo de carga (ejecutar varias veces)
# Deberías ver respuestas de web1 (EN) y web2 (ES) alternándose
curl -i http://localhost

# 5. Verificar que la cabecera X-Backend-Served-By muestra el backend que respondió
curl -I http://localhost

# 6. Enviar un registro a través de la API
curl -X POST -H "Content-Type: application/json" \
  -d '{"name": "Test User", "comuna": 7, "carrera": "Ingeniería"}' \
  http://localhost/api/register

# 7. Probar el endpoint de estadísticas (requiere autenticación)
# Reemplaza <ADMIN_USER> y <ADMIN_PASS> con tus credenciales del .env
curl -u "${ADMIN_USER}:${ADMIN_PASS}" -X POST http://localhost:5010/admin/send-stats

# 8. Para detener y limpiar todo
docker-compose down -v --remove-orphans
```

## Paso 4 — Aprovisionamiento de Infraestructura en AWS

*   **Objetivo:** Crear 4 VMs EC2 y un Security Group con las reglas de firewall necesarias.
*   **Explicación:** Usaremos la AWS CLI para crear la infraestructura. El script `init-ec2.sh` se pasará como `user-data` para que cada VM instale Docker y se prepare para unirse al clúster de Swarm.
*   **Ruta Robusta (Producción):

### 1. Crear `infra/init-ec2.sh`
Este script prepara cada nodo.
```bash
#!/bin/bash
# User-data script para configurar una instancia EC2 para Docker Swarm

# Actualizar paquetes e instalar dependencias
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# Instalar Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
sudo apt-get update -y
sudo apt-get install -y docker-ce

# Añadir el usuario 'ubuntu' al grupo de docker para ejecutar comandos sin sudo
sudo usermod -aG docker ubuntu

# Habilitar e iniciar el servicio de Docker
sudo systemctl enable docker
sudo systemctl start docker

echo "Instalación de Docker completada."
```

### 2. Comandos AWS CLI
Ejecuta estos comandos desde tu máquina local (requiere AWS CLI configurado).

```bash
# Shell: bash/zsh

# --- Variables (reemplaza con tus valores) ---
AWS_REGION="us-east-1"
KEY_NAME="<TU_KEY_PAIR_NAME>" # El nombre de tu par de claves EC2
AMI_ID="ami-0c55b159cbfafe1f0" # Ubuntu 22.04 LTS (amd64) para us-east-1, verifica la AMI para tu región
INSTANCE_TYPE="t2.micro" # Tipo de instancia (Amazon Educate)
VPC_ID=$(aws ec2 describe-vpcs --query "Vpcs[?IsDefault].VpcId" --output text)

# --- 1. Crear Security Group ---
echo "Creando Security Group..."
SG_ID=$(aws ec2 create-security-group \
  --group-name "swarm-cluster-sg" \
  --description "Security group para el clúster de Docker Swarm" \
  --vpc-id "$VPC_ID" \
  --query "GroupId" --output text)
echo "Security Group creado con ID: $SG_ID"

# --- 2. Añadir Reglas de Firewall ---
MY_IP=$(curl -s https://checkip.amazonaws.com)
echo "Tu IP pública es: $MY_IP. Se usará para el acceso SSH."

# Reglas para acceso público y entre nodos del clúster
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 22 --cidr "$MY_IP/32" # SSH (solo desde tu IP)
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 80 --cidr "0.0.0.0/0"  # HTTP
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 443 --cidr "0.0.0.0/0" # HTTPS
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 2377 --source-group "$SG_ID" # Swarm management
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol tcp --port 7946 --source-group "$SG_ID" # Swarm node communication
aws ec2 authorize-security-group-ingress --group-id "$SG_ID" --protocol udp --port 7946 --source-group "$SG_ID" # Swarm node communication
aws ec2 authorize-security-group-ingress --group-id "$SGID" --protocol udp --port 4789 --source-group "$SG_ID" # Swarm overlay network

# ¡IMPORTANTE! La regla para Postgres NO se añade aquí.
# La base de datos no debe ser accesible desde internet.
# Los servicios dentro de la red overlay de Docker podrán comunicarse.

# --- 3. Lanzar las 4 Instancias EC2 ---
echo "Lanzando 4 instancias EC2..."
aws ec2 run-instances \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SG_ID" \
  --user-data file://infra/init-ec2.sh \
  --count 4 \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Project,Value=SwarmCluster}]'

echo "Instancias lanzadas. Espera unos minutos para que se inicialicen."

# --- 4. Obtener IPs públicas de las instancias ---
echo "Obteniendo IPs públicas de las instancias creadas..."
aws ec2 describe-instances \
  --filters "Name=tag:Project,Values=SwarmCluster" "Name=instance-state-name,Values=running" \
  --query "Reservations[*].Instances[*].PublicIpAddress" \
  --output text
```

## Paso 5 — Configuración del Clúster (Docker Swarm)

*   **Objetivo:** Inicializar el clúster de Swarm, unir los nodos y etiquetarlos según su rol.
*   **Explicación:** Un nodo será el `manager` (orquestador) y los otros 3 serán `workers`. Asignaremos etiquetas (`labels`) a cada nodo para poder dirigir servicios específicos a ellos (ej. la base de datos a un nodo concreto).
*   **Ruta Robusta (Producción):

### Comandos de configuración
```bash
# Shell: bash/zsh

# --- Variables (reemplaza con las IPs obtenidas en el paso anterior) ---
MANAGER_IP="<IP_NODO_1>"
WORKER1_IP="<IP_NODO_2>"
WORKER2_IP="<IP_NODO_3>"
WORKER3_IP="<IP_NODO_4>"
SSH_USER="ubuntu" # Usuario por defecto en instancias Ubuntu
SSH_KEY="~/.ssh/<TU_KEY_PAIR_NAME>.pem" # Ruta a tu clave privada

# --- 1. Inicializar Swarm en el nodo Manager ---
# Conéctate al primer nodo y ejecuta:
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker swarm init --advertise-addr ${MANAGER_IP}"

# Copia el comando 'docker swarm join' que se muestra en la salida.
# Se verá algo como: docker swarm join --token <TOKEN> <MANAGER_IP>:2377

# --- 2. Unir los Workers al Clúster ---
# Pega el comando copiado en los otros 3 nodos:
ssh -i "$SSH_KEY" "${SSH_USER}@${WORKER1_IP}" "<PEGA_EL_COMANDO_JOIN_AQUÍ>"
ssh -i "$SSH_KEY" "${SSH_USER}@${WORKER2_IP}" "<PEGA_EL_COMANDO_JOIN_AQUÍ>"
ssh -i "$SSH_KEY" "${SSH_USER}@${WORKER3_IP}" "<PEGA_EL_COMANDO_JOIN_AQUÍ>"

# --- 3. Verificar que los nodos están unidos ---
# Desde el nodo Manager:
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker node ls"

# --- 4. Etiquetar los nodos ---
# Desde el nodo Manager, asigna roles a cada nodo.
# Esto es crucial para el 'placement' en docker-stack.yml.
# Obtén los HOSTNAMES de la salida de 'docker node ls'

MANAGER_HOSTNAME="<HOSTNAME_NODO_1>"
WORKER1_HOSTNAME="<HOSTNAME_NODO_2>"
WORKER2_HOSTNAME="<HOSTNAME_NODO_3>"
WORKER3_HOSTNAME="<HOSTNAME_NODO_4>"

# Asignar roles:
# Nodo Manager: será el balanceador de carga.
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker node update --label-add role=lb ${MANAGER_HOSTNAME}"

# Worker 1: correrá la base de datos y el servicio de stats.
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker node update --label-add role=data ${WORKER1_HOSTNAME}"

# Workers 2 y 3: correrán las aplicaciones web.
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker node update --label-add role=web_en ${WORKER2_HOSTNAME}"
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker node update --label-add role=web_es ${WORKER3_HOSTNAME}"

# --- 5. Verificar etiquetas ---
# Desde el nodo Manager:
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker node inspect \
$(docker node ls -q) --format '{{.Description.Hostname}} -> {{.Spec.Labels}}'"
```

## Paso 6 — Despliegue en Producción (Docker Stack)

*   **Objetivo:** Desplegar toda la pila de servicios en el clúster de Swarm usando un archivo `docker-stack.yml`.
*   **Explicación:** Este archivo es similar a `docker-compose.yml` pero adaptado para Swarm. Usa `deploy` para definir réplicas, políticas de reinicio y `placement constraints` (basadas en las etiquetas que acabamos de crear). Las credenciales se manejan con `secrets` de Docker, que son más seguros.
*   **Ruta Robusta (Producción):

### 1. Crear `docker-stack.yml`
```yaml
version: "3.8" 

secrets:
  db_pass:
    external: true
  # Para producción, también deberías usar secrets para esto:
  # admin_pass:
  #   external: true
  # smtp_pass:
  #   external: true

networks:
  mynet:
    driver: overlay
    attachable: true

volumes:
  db_data:

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: appdb
      POSTGRES_USER: appuser
      POSTGRES_PASSWORD_FILE: /run/secrets/db_pass
    secrets:
      - db_pass
    volumes:
      - db_data:/var/lib/postgresql/data
      - ./infra/schema.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - mynet
    deploy:
      replicas: 1
      placement:
        constraints: [node.labels.role == data]
      restart_policy:
        condition: on-failure

  web1:
    image: <TU_USUARIO_DOCKERHUB>/web_app:latest
    environment:
      - LANG=en
      - DB_HOST=db
      - DB_NAME=appdb
      - DB_USER=appuser
      - PYTHONUNBUFFERED=1
    secrets:
      - source: db_pass
        target: db_pass # Lo expone como archivo en /run/secrets/db_pass
    networks:
      - mynet
    deploy:
      replicas: 1
      placement:
        constraints: [node.labels.role == web_en]
      restart_policy:
        condition: any

  web2:
    image: <TU_USUARIO_DOCKERHUB>/web_app:latest
    environment:
      - LANG=es
      - DB_HOST=db
      - DB_NAME=appdb
      - DB_USER=appuser
      - PYTHONUNBUFFERED=1
    secrets:
      - source: db_pass
        target: db_pass
    networks:
      - mynet
    deploy:
      replicas: 1
      placement:
        constraints: [node.labels.role == web_es]
      restart_policy:
        condition: any

  stats:
    image: <TU_USUARIO_DOCKERHUB>/stats_app:latest
    environment:
      - DB_HOST=db
      - DB_NAME=appdb
      - DB_USER=appuser
      - ADMIN_USER=<TU_ADMIN_USER_SEGURO>
      - ADMIN_PASS=<TU_ADMIN_PASS_SEGURO> # Mejor usar secrets
      - EMAIL_MODE=ses # Cambiar a 'ses' para producción
      - EMAIL_FROM=<TU_EMAIL_VERIFICADO_EN_SES> # AWS CLI lo tomará del rol de la instancia
      - AWS_REGION=${AWS_REGION} 
      - PYTHONUNBUFFERED=1
    secrets:
      - source: db_pass
        target: db_pass
    networks:
      - mynet
    deploy:
      replicas: 1
      placement:
        constraints: [node.labels.role == data]
      restart_policy:
        condition: on-failure

  lb:
    image: <TU_USUARIO_DOCKERHUB>/load_balancer:latest
    environment:
      # Swarm DNS resolverá 'tasks.web1' y 'tasks.web2' a las IPs de los contenedores
      - BACKENDS=http://web1:5000,http://web2:5000
      - PYTHONUNBUFFERED=1
    ports:
      - target: 8000
        published: 80
        protocol: tcp
        mode: ingress
    networks:
      - mynet
    deploy:
      replicas: 2 # 2 réplicas para alta disponibilidad
      placement:
        constraints: [node.labels.role == lb]
      restart_policy:
        condition: any
```

### 2. Comandos de Despliegue
```bash
# Shell: bash/zsh

# --- Variables ---
DOCKERHUB_USER="<TU_USUARIO_DOCKERHUB>"
MANAGER_IP="<IP_NODO_MANAGER>"
SSH_USER="ubuntu"
SSH_KEY="~/.ssh/<TU_KEY_PAIR_NAME>.pem"

# --- 1. Construir y subir imágenes a Docker Hub ---
# (Asegúrate de haber iniciado sesión con 'docker login')
docker build -t "${DOCKERHUB_USER}/web_app:latest" ./web_app
docker build -t "${DOCKERHUB_USER}/stats_app:latest" ./stats_app
docker build -t "${DOCKERHUB_USER}/load_balancer:latest" ./load_balancer

docker push "${DOCKERHUB_USER}/web_app:latest"
docker push "${DOCKERHUB_USER}/stats_app:latest"
docker push "${DOCKERHUB_USER}/load_balancer:latest"

# --- 2. Crear el secret para la contraseña de la BD en el Swarm ---
# Desde el nodo Manager:
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" \
  "echo '<TU_PASSWORD_DE_BD_ULTRASECRETA>' | docker secret create db_pass -"

# --- 3. Desplegar el stack ---
# Copia el stack file al manager y despliega
scp -i "$SSH_KEY" docker-stack.yml "${SSH_USER}@${MANAGER_IP}:~/")
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" \
  "docker stack deploy -c docker-stack.yml mystack"

# --- 4. Comandos de Verificación (desde el manager) ---
# Listar servicios del stack
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker stack services mystack"

# Ver logs de un servicio (ej. web1)
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker service logs mystack_web1 -f"

# Ver logs del balanceador
ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker service logs mystack_lb -f"
```

## Paso 7 — Configuración de DNS y HTTPS

*   **Objetivo:** Apuntar un dominio público al balanceador de carga y habilitar HTTPS.
*   **Explicación:**
    *   **DNS (Freenom):** Debes crear un registro `A` en tu panel de Freenom que apunte tu dominio (ej. `mi-proyecto.tk`) a la IP pública de tu nodo manager (el que tiene la etiqueta `role=lb`).
    *   **HTTPS (Let's Encrypt):** La forma más robusta es usar un proxy reverso como Nginx o Traefik delante de tu balanceador. Traefik tiene integración nativa con Docker Swarm y Let's Encrypt, automatizando la creación y renovación de certificados. Implementarlo está fuera del alcance de esta guía inicial, pero es el siguiente paso crítico para producción.
*   **Instrucciones DNS (Freenom):**
    1.  Ve a Freenom > My Domains > Manage Domain > Manage Freenom DNS.
    2.  Añade un nuevo registro:
        *   **Name:** `@` (o déjalo en blanco para el dominio raíz) o `www` para `www.dominio.tk`.
        *   **Type:** `A`
        *   **TTL:** `3600` (o el valor por defecto).
        *   **Target:** `<IP_PUBLICA_DE_TU_NODO_MANAGER>`
    3.  Guarda los cambios. La propagación puede tardar desde unos minutos hasta varias horas.
*   **Verificación DNS:
    ```bash
    # Desde tu máquina local, después de un tiempo de propagación
    ping <TU_DOMINIO.TK>
    # Debería resolver a la IP de tu manager.
    ```

## Paso 8 — CI/CD con GitHub Actions

*   **Objetivo:** Automatizar la construcción y publicación de imágenes Docker en cada `push` a la rama `main`.
*   **Explicación:** El workflow `.github/workflows/docker-publish.yml` se activa automáticamente. Solo necesitas configurar los secretos en tu repositorio de GitHub.
*   **Configuración de Secretos en GitHub:**
    1.  Ve a tu repositorio en GitHub > Settings > Secrets and variables > Actions.
    2.  Crea dos nuevos "Repository secrets":
        *   `DOCKERHUB_USERNAME`: Tu nombre de usuario de Docker Hub.
        *   `DOCKERHUB_TOKEN`: Un token de acceso generado desde tu cuenta de Docker Hub (Account Settings > Security > New Access Token).
*   **Archivo `.github/workflows/docker-publish.yml` (ya está correcto en tu repo):
    ```yaml
    name: Build and Push Docker images
    on:
      push:
        branches: [ "main" ]

    jobs:
      build:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4

          - name: Set up Docker Buildx
            uses: docker/setup-buildx-action@v3

          - name: Log in to DockerHub
            uses: docker/login-action@v3
            with:
              username: ${{ secrets.DOCKERHUB_USERNAME }}
              password: ${{ secrets.DOCKERHUB_TOKEN }}

          - name: Build and push web_app
            uses: docker/build-push-action@v5
            with:
              context: ./web_app
              push: true
              tags: ${{ secrets.DOCKERHUB_USERNAME }}/web_app:latest

          - name: Build and push stats_app
            uses: docker/build-push-action@v5
            with:
              context: ./stats_app
              push: true
              tags: ${{ secrets.DOCKERHUB_USERNAME }}/stats_app:latest

          - name: Build and push load_balancer
            uses: docker/build-push-action@v5
            with:
              context: ./load_balancer
              push: true
              tags: ${{ secrets.DOCKERHUB_USERNAME }}/load_balancer:latest
    ```
*   **Para actualizar el stack después de un push:**
    Después de que el workflow termine, las imágenes `latest` estarán actualizadas. Para que Swarm use las nuevas, conéctate al manager y ejecuta:
    ```bash
    ssh -i "$SSH_KEY" "${SSH_USER}@${MANAGER_IP}" "docker stack deploy -c docker-stack.yml mystack"
    ```

## Paso 9 — Pruebas, Documentación y Monitoreo

*   **Objetivo:** Validar el despliegue, documentar el proyecto y establecer un monitoreo básico.
*   **Pruebas de Carga y Funcionalidad:
    ```bash
    # 1. Verificar Round-Robin (ejecutar 10 veces)
    for i in {1..10}; do curl -s -I http://<TU_DOMINIO.TK> | grep 'X-Backend-Served-By'; sleep 0.5; done
    # Deberías ver la cabecera alternar entre web1 y web2.

    # 2. Prueba de carga básica con 'ab' (Apache Bench)
    # 100 peticiones, 10 concurrentes
    ab -n 100 -c 10 http://<TU_DOMINIO.TK>/

    # 3. Verificar métricas del balanceador
    curl http://<TU_DOMINIO.TK>/lb/metrics
    ```
*   **Plantilla de Documentación (`docs/report.md`):**
    He creado una plantilla básica. Debes completarla con:
    *   Un diagrama de la arquitectura final.
    *   Capturas de pantalla de las pruebas.
    *   Explicación de las decisiones de diseño.
*   **Checklist de Entrega:**
    - [ ] Código fuente corregido y subido a Git.
    - [ ] `Dockerfile` optimizados y subidos.
    - [ ] `docker-compose.yml` y `.env` para entorno local.
    - [ ] `docker-stack.yml` para producción.
    - [ ] Script `init-ec2.sh` para aprovisionamiento.
    - [ ] Security Group y 4 instancias EC2 creadas en AWS.
    - [ ] Clúster de Swarm inicializado, nodos unidos y etiquetados.
    - [ ] Secret de `db_pass` creado en Swarm.
    - [ ] Stack desplegado exitosamente.
    - [ ] Dominio (Freenom) apuntando a la IP del manager.
    - [ ] Pruebas de Round-Robin y carga realizadas.
    - [ ] `docs/report.md` completado.

## Paso Final — Explicaciones Didácticas y Acciones Urgentes

### Explicaciones (una frase por herramienta)
*   **AWS:** Proveedor de nube que nos da las máquinas virtuales (EC2) y servicios como el de envío de correo (SES).
*   **Docker:** Herramienta que empaqueta nuestras aplicaciones y sus dependencias en "contenedores" portátiles y aislados.
*   **Docker Compose:** Orquestador para definir y correr aplicaciones Docker multi-contenedor en una sola máquina (ideal para desarrollo).
*   **Docker Swarm:** Orquestador nativo de Docker para distribuir y gestionar contenedores a través de un clúster de múltiples máquinas.
*   **PostgreSQL:** Sistema de gestión de bases de datos relacional, robusto y de código abierto, que usamos para almacenar los datos de los usuarios.
*   **Freenom:** Proveedor de dominios gratuitos que usamos para darle un nombre público a nuestro servicio.
*   **GitHub Actions:** Herramienta de CI/CD integrada en GitHub que automatiza tareas como construir y publicar nuestras imágenes Docker.
*   **Matplotlib:** Biblioteca de Python para generar gráficas y visualizaciones de datos estáticas.
*   **Gunicorn/Uvicorn:** Servidores de aplicaciones WSGI/ASGI de grado de producción para correr nuestras apps de Python (Flask/FastAPI) de forma eficiente.
*   **FastAPI/httpx:** Framework moderno y cliente HTTP asíncrono que usamos para construir nuestro balanceador de carga de alto rendimiento.

---

# ACCIONES URGENTES (para tenerlo desplegable en 24h)

1.  **Configura tus Secretos en GitHub:** Ve a tu repositorio y añade `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN`. Sin esto, el CI/CD fallará.
2.  **Crea un Par de Claves en AWS EC2:** Necesitas un Key Pair para poder acceder a tus instancias vía SSH. Anota su nombre (`<TU_KEY_PAIR_NAME>`).
3.  **Ejecuta el Script de AWS CLI (Paso 4):** Lanza las instancias y configura el Security Group. Este es el paso que más tiempo consume.
4.  **Configura el Clúster de Swarm (Paso 5):** Conéctate a las IPs generadas y ejecuta los comandos `docker swarm init`, `join` y `node update`.
5.  **Crea el Secret y Despliega el Stack (Paso 6):** Reemplaza los placeholders en `docker-stack.yml` (tu usuario de Docker Hub), crea el `db_pass` en el manager y ejecuta `docker stack deploy`.

Una vez completados estos 5 puntos, tu aplicación estará en línea y funcionando en AWS.
