from flask import Flask, request, jsonify
import os, io, base64
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.message import EmailMessage
from functools import wraps
import json
from sqlalchemy import create_engine
app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASS = os.getenv("DB_PASS", "apppass")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "adminpass")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.mailtrap.io")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")

def get_conn():
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)

def check_auth(u, p):
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
    conn = get_conn()
    engine = create_engine(f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
    df = pd.read_sql("SELECT name, comuna, date, carrera, lang FROM users", engine, parse_dates=["date"])
    conn.close()
    return df

def build_plots(df):
    buf_images = []
    # Example plot: counts per carrera
    fig1 = plt.figure()
    df['carrera'] = df['carrera'].fillna('Unknown')
    df['carrera'].value_counts().plot(kind='bar', title='Counts per Carrera')
    fig1.tight_layout()
    img_buf1 = io.BytesIO()
    fig1.savefig(img_buf1, format='png')
    img_buf1.seek(0)
    buf_images.append(('carrera.png', img_buf1.read()))
    plt.close(fig1)

    # Example plot: counts per comuna
    fig2 = plt.figure()
    df['comuna'].value_counts().sort_index().plot(kind='bar', title='Counts per Comuna')
    fig2.tight_layout()
    img_buf2 = io.BytesIO()
    fig2.savefig(img_buf2, format='png')
    img_buf2.seek(0)
    buf_images.append(('comuna.png', img_buf2.read()))
    plt.close(fig2)

    return buf_images

def build_pdf(images):
    pdf_buf = io.BytesIO()
    with PdfPages(pdf_buf) as pdf:
        for name, img_bytes in images:
            img = plt.imread(io.BytesIO(img_bytes))
            fig = plt.figure(figsize=(8,6))
            plt.imshow(img)
            plt.axis('off')
            pdf.savefig(fig)
            plt.close(fig)
    pdf_buf.seek(0)
    return pdf_buf

def send_email(to_email, subject, body, attachments):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = os.getenv("EMAIL_FROM", "no-reply@example.com")
    msg['To'] = to_email
    msg.set_content(body)
    for name, content, mime in attachments:
        msg.add_attachment(content, maintype=mime.split('/')[0], subtype=mime.split('/')[1], filename=name)
    # SMTP
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        if SMTP_USER:
            s.login(SMTP_USER, SMTP_PASS)
        s.send_message(msg)

@app.route("/admin/send-stats", methods=["POST"])
@requires_auth
def send_stats():
    to_email = request.json.get("to") if request.json and "to" in request.json else "ialondonoo@eafit.edu.co"
    df = fetch_data()
    images = build_plots(df)
    pdf_buf = build_pdf(images)
    # attachments: add PDF and PNGs
    attachments = []
    attachments.append(("stats.pdf", pdf_buf.read(), "application/pdf"))
    # send
    pdf_buf.seek(0)
    send_email(to_email, "Statistics Report", "Attached stats report.", [("stats.pdf", pdf_buf.read(), "application/pdf")])
    return jsonify({"status":"sent","to":to_email})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5010)
