from flask import Flask, request, render_template, redirect, url_for, jsonify
import os
import psycopg2
import datetime
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
LANG = os.getenv("LANG", "en")  # "en" or "es"
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASS = os.getenv("DB_PASS", "apppass")

def get_conn():
    return psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME, user=DB_USER, password=DB_PASS)

@app.route("/")
def index():
    title = "User Registration" if LANG.startswith("en") else "Registro de Usuarios"
    return render_template("index.html", title=title, lang=LANG)

@app.route("/register", methods=["POST"])
def register():
    name = request.form.get("name")
    comuna = int(request.form.get("comuna", 1))
    carrera = request.form.get("carrera")
    fecha = datetime.datetime.utcnow()

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (name, comuna, date, carrera, lang) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (name, comuna, fecha, carrera, LANG)
    )
    conn.commit()
    cur.close()
    conn.close()
    message = "Registered" if LANG.startswith("en") else "Registrado"
    return redirect(url_for("index"))

@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.json or request.form
    name = data.get("name")
    comuna = int(data.get("comuna", 1))
    carrera = data.get("carrera")
    fecha = datetime.datetime.utcnow()
    conn = get_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        "INSERT INTO users (name, comuna, date, carrera, lang) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (name, comuna, fecha, carrera, LANG)
    )
    new_id = cur.fetchone()["id"]
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"id": new_id, "status": "ok"}), 201

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
