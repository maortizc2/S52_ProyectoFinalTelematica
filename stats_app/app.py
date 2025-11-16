# =================================================================
# APLICACIÓN DE ESTADÍSTICAS Y REPORTES
# =================================================================
# Esta aplicación se conecta a la base de datos, genera un gráfico
# de estadísticas sobre los usuarios registrados y lo envía por correo.
# =================================================================

import os
import psycopg2
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from flask import Flask, jsonify, send_file
from dotenv import load_dotenv

# --- Inicialización y Configuración ---
# Configura Matplotlib para funcionar en un entorno sin GUI (headless).
matplotlib.use('Agg')
# Carga las variables de entorno desde el archivo .env.
load_dotenv()

app = Flask(__name__)

# --- Lectura de Variables de Entorno ---
DATABASE_URL = os.getenv("DATABASE_URL")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SENDER_EMAIL_SMTP = "stats-noreply@demomailtrap.co"

def get_db_data():
    """
    Obtiene los datos de la tabla 'usuarios' y los devuelve como un DataFrame de Pandas.
    """
    try:
        # Conecta a la base de datos.
        conn = psycopg2.connect(DATABASE_URL)
        # Consulta para contar usuarios por carrera de interés.
        query = "SELECT carrera_interes, COUNT(*) as total FROM usuarios GROUP BY carrera_interes ORDER BY total DESC;"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error al conectar o consultar la BD: {e}")
        return None

def create_stats_chart(df):
    """
    Genera un gráfico de barras a partir de un DataFrame y lo devuelve como un buffer de bytes.
    """
    if df is None or df.empty:
        return None
        
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Crea el gráfico de barras.
    df.plot(kind='bar', x='carrera_interes', y='total', ax=ax, legend=False, color='#1877f2')
    
    # Personaliza el gráfico.
    ax.set_title('Registros de Usuarios por Carrera de Interés', fontsize=16, weight='bold')
    ax.set_xlabel('Carrera de Interés', fontsize=12)
    ax.set_ylabel('Número de Registros', fontsize=12)
    ax.tick_params(axis='x', rotation=45, labelsize=11)
    plt.tight_layout()
    
    # Guarda el gráfico en un buffer en memoria para no tener que escribirlo en disco.
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf

def send_email_mailtrap(attachment_buffer):
    """
    Envía un correo electrónico con el gráfico adjunto usando Mailtrap como servidor SMTP.
    """
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS]):
        raise ValueError("Faltan variables de entorno para Mailtrap.")

    # Construye el mensaje de correo.
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL_SMTP
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = "Reporte de Estadísticas de Usuarios"
    
    msg.attach(MIMEText("Adjunto encontrarás el reporte de estadísticas de registros por carrera.", 'plain'))
    
    # Adjunta la imagen del gráfico.
    part = MIMEApplication(attachment_buffer.read(), Name="stats_report.png")
    part['Content-Disposition'] = 'attachment; filename="stats_report.png"'
    msg.attach(part)
    
    # Conecta al servidor SMTP y envía el correo.
    with smtplib.SMTP(SMTP_HOST, int(SMTP_PORT)) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print(f"Correo enviado exitosamente a {RECIPIENT_EMAIL} a través de Mailtrap.")

@app.route('/stats/generate-chart', methods=['GET'])
def generate_chart_endpoint():
    """
    Endpoint para generar el gráfico y devolverlo como una imagen PNG.
    Útil para previsualizar el gráfico sin enviar el correo.
    """
    df = get_db_data()
    if df is None or df.empty:
        return jsonify({"error": "No se pudieron obtener datos o no hay datos para reportar."}), 404
        
    chart_buffer = create_stats_chart(df)
    if chart_buffer is None:
        return jsonify({"error": "No se pudo generar el gráfico."}), 500

    return send_file(chart_buffer, mimetype='image/png')

@app.route('/stats/send-report', methods=['GET'])
def send_stats_endpoint():
    """
    Endpoint principal para generar el gráfico y enviarlo por correo.
    Cambiado a GET para facilitar la prueba desde un navegador.
    """
    df = get_db_data()
    if df is None or df.empty:
        return jsonify({"error": "No hay datos para reportar."}), 404
        
    chart_buffer = create_stats_chart(df)
    if chart_buffer is None:
        return jsonify({"error": "No se pudo generar el gráfico."}), 500

    try:
        send_email_mailtrap(chart_buffer)
        return jsonify({"message": f"Estadísticas enviadas exitosamente a {RECIPIENT_EMAIL}."})
    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return jsonify({"error": "Ocurrió un error al enviar el correo.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)