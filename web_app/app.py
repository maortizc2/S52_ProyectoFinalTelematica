import os
import psycopg2
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (para desarrollo local)
load_dotenv()

app = Flask(__name__)

# --- Configuración ---
# Lee la URL de la base de datos y el idioma del servidor desde el entorno
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/mydatabase")
LANG = os.getenv("LANG", "en") # 'en' para inglés, 'es' para español

# --- Textos para internacionalización (i18n) ---
TEXTS = {
    "en": {
        "title": "User Registration",
        "header": "Register a New User",
        "name_label": "Name:",
        "comuna_label": "District (1-10):",
        "carrera_label": "Major:",
        "submit_button": "Register",
        "success_message": "User registered successfully!",
        "error_db_connection": "Database connection error.",
        "error_db_insert": "Error inserting data into the database."
    },
    "es": {
        "title": "Registro de Usuario",
        "header": "Registrar un Nuevo Usuario",
        "name_label": "Nombre:",
        "comuna_label": "Comuna (1-10):",
        "carrera_label": "Carrera:",
        "submit_button": "Registrar",
        "success_message": "¡Usuario registrado con éxito!",
        "error_db_connection": "Error de conexión con la base de datos.",
        "error_db_insert": "Error al insertar datos en la base de datos."
    }
}
CARRERAS = ["Medicina", "Ingeniería", "Abogacía", "Licenciatura", "Arquitectura"]

def get_db_connection():
    """Establece la conexión con la base de datos."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError:
        return None

@app.route('/')
def index():
    """Muestra el formulario de registro."""
    # Selecciona los textos según el idioma configurado
    lang_texts = TEXTS.get(LANG, TEXTS["en"])
    return render_template('index.html', texts=lang_texts, carreras=CARRERAS, lang=LANG)

@app.route('/register', methods=['POST'])
def register():
    """Recibe los datos del formulario y los inserta en la base de datos."""
    lang_texts = TEXTS.get(LANG, TEXTS["en"])
    conn = None
    try:
        name = request.form['name']
        comuna = int(request.form['comuna'])
        carrera = request.form['carrera']

        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": lang_texts["error_db_connection"]}), 500

        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (name, comuna, carrera, lang) VALUES (%s, %s, %s, %s)",
            (name, comuna, carrera, LANG)
        )
        conn.commit()
        cur.close()
        
        return jsonify({"message": lang_texts["success_message"]})

    except Exception as e:
        print(f"Error en /register: {e}")
        return jsonify({"error": lang_texts["error_db_insert"], "details": str(e)}), 500
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # El modo debug no es para producción. Gunicorn será el servidor en producción.
    app.run(host='0.0.0.0', port=5000, debug=True)
