import os
import psycopg2
import pandas as pd
import matplotlib.pyplot as plt
import io
import smtplib
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# --- Configuración General ---
DATABASE_URL = os.getenv("DATABASE_URL")
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "mailtrap") # 'mailtrap' o 'ses'
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL", "ialondonoo@eafit.edu.co")

# --- Configuración Mailtrap ---
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = os.getenv("SMTP_PORT", 587)
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SENDER_EMAIL_SMTP = "stats-noreply@my-project.com"

# --- Configuración AWS SES ---
AWS_REGION = os.getenv("AWS_REGION")
SENDER_EMAIL_SES = os.getenv("SENDER_EMAIL_SES") # Debe ser una identidad verificada en SES

def get_db_data():
    """Obtiene los datos de la base de datos y los devuelve como un DataFrame de Pandas."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # Consulta para contar registros por carrera
        query = "SELECT carrera, COUNT(*) as count FROM users GROUP BY carrera ORDER BY count DESC;"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        print(f"Error al conectar o consultar la BD: {e}")
        return None

def create_stats_chart(df):
    """Genera un gráfico de barras a partir de un DataFrame y lo devuelve como bytes."""
    if df.empty:
        return None
        
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(10, 6))
    
    df.plot(kind='bar', x='carrera', y='count', ax=ax, legend=False, color='skyblue')
    
    ax.set_title('Registros por Carrera', fontsize=16)
    ax.set_xlabel('Carrera', fontsize=12)
    ax.set_ylabel('Número de Registros', fontsize=12)
    ax.tick_params(axis='x', rotation=45)
    plt.tight_layout()
    
    # Guardar el gráfico en un buffer en memoria
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    return buf

def send_email_mailtrap(attachment_buffer):
    """Envía el correo usando SMTP (Mailtrap)."""
    if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS]):
        raise ValueError("Faltan variables de entorno para Mailtrap (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)")

    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL_SMTP
    msg['To'] = RECIPIENT_EMAIL
    msg['Subject'] = "Reporte de Estadísticas de Usuarios"
    
    msg.attach(MIMEText("Adjunto encontrarás el reporte de estadísticas de registros por carrera.", 'plain'))
    
    part = MIMEApplication(attachment_buffer.read(), Name="stats_report.png")
    part['Content-Disposition'] = 'attachment; filename="stats_report.png"'
    msg.attach(part)
    
    with smtplib.SMTP(SMTP_HOST, int(SMTP_PORT)) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
    print("Correo enviado exitosamente a través de Mailtrap.")

def send_email_ses(attachment_buffer):
    """Envía el correo usando AWS SES."""
    if not all([AWS_REGION, SENDER_EMAIL_SES]):
        raise ValueError("Faltan variables de entorno para AWS SES (AWS_REGION, SENDER_EMAIL_SES)")

    client = boto3.client('ses', region_name=AWS_REGION)
    
    msg = MIMEMultipart()
    msg['Subject'] = "Reporte de Estadísticas de Usuarios"
    msg['From'] = SENDER_EMAIL_SES
    msg['To'] = RECIPIENT_EMAIL
    
    msg.attach(MIMEText("Adjunto encontrarás el reporte de estadísticas de registros por carrera.", 'plain'))
    
    part = MIMEApplication(attachment_buffer.read(), Name="stats_report.png")
    part['Content-Disposition'] = 'attachment; filename="stats_report.png"'
    msg.attach(part)

    try:
        response = client.send_raw_email(
            Source=SENDER_EMAIL_SES,
            Destinations=[RECIPIENT_EMAIL],
            RawMessage={'Data': msg.as_string()}
        )
        print(f"Correo enviado exitosamente a través de AWS SES. Message ID: {response['MessageId']}")
    except ClientError as e:
        print(f"Error al enviar correo con SES: {e.response['Error']['Message']}")
        raise

@app.route('/admin/send-stats', methods=['POST'])
def send_stats():
    """Endpoint principal para generar y enviar las estadísticas."""
    # Opcional: Proteger este endpoint con una clave de API
    # api_key = request.headers.get('X-API-KEY')
    # if api_key != os.getenv("STATS_API_KEY"):
    #     return jsonify({"error": "No autorizado"}), 401

    df = get_db_data()
    if df is None or df.empty:
        return jsonify({"error": "No se pudieron obtener datos o no hay datos para reportar."}), 500
        
    chart_buffer = create_stats_chart(df)
    if chart_buffer is None:
        return jsonify({"error": "No se pudo generar el gráfico."}), 500

    try:
        if EMAIL_PROVIDER == 'ses':
            send_email_ses(chart_buffer)
            provider_used = 'AWS SES'
        elif EMAIL_PROVIDER == 'mailtrap':
            send_email_mailtrap(chart_buffer)
            provider_used = 'Mailtrap'
        else:
            return jsonify({"error": f"Proveedor de email no soportado: {EMAIL_PROVIDER}"}), 400
        
        return jsonify({"message": f"Estadísticas enviadas exitosamente a {RECIPIENT_EMAIL} usando {provider_used}."})

    except Exception as e:
        print(f"Error al enviar el correo: {e}")
        return jsonify({"error": "Ocurrió un error al enviar el correo.", "details": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
