# =================================================================
# APLICACIÓN WEB FLASK (SERVIDOR WEB)
# =================================================================
# Esta aplicación sirve un formulario de registro de usuarios.
# Se conecta a una base de datos PostgreSQL para almacenar los datos.
# La aplicación puede configurarse para mostrarse en inglés o español.
# =================================================================

import os
import psycopg2
from flask import Flask, request, render_template, jsonify
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (útil para desarrollo local)
load_dotenv()

app = Flask(__name__, template_folder='templates')

# --- Configuración de la Aplicación ---
# Lee la URL de la base de datos y el idioma del servidor desde las variables de entorno.
DATABASE_URL = os.getenv("DATABASE_URL")
LANG = os.getenv("LANG", "en")  # 'en' para inglés (default), 'es' para español
PORT = os.getenv("PORT", 8000)

# --- Datos para los Formularios ---
# Lista de carreras que se mostrarán en el formulario.
# Coincide con el tipo ENUM 'carrera_type' definido en 'infra/init.sql'.
CARRERAS = ["Medicina", "Ingeniería", "Abogacía", "Licenciatura"]

def get_db_connection():
    """
    Establece y devuelve una conexión con la base de datos PostgreSQL.
    Devuelve None si la conexión falla.
    """
    try:
        # Se conecta utilizando la URL proporcionada en las variables de entorno.
        conn = psycopg2.connect(DATABASE_URL)
        return conn
    except psycopg2.OperationalError as e:
        # Captura errores de conexión (ej. host no encontrado, credenciales incorrectas).
        print(f"Error de conexión con la base de datos: {e}")
        return None

@app.route('/')
def index():
    """
    Muestra la página principal con el formulario de registro.
    Selecciona la plantilla HTML (inglés o español) según la variable de entorno LANG.
    """
    # Construye el nombre del template a renderizar.
    template_name = f"index_{LANG}.html"
    # Renderiza la plantilla, pasando la lista de carreras para el menú desplegable.
    return render_template(template_name, carreras=CARRERAS)

@app.route('/register', methods=['POST'])
def register():
    """
    Recibe los datos del formulario y los inserta en la base de datos.
    Este endpoint es llamado por una petición AJAX desde el frontend.
    """
    conn = None
    try:
        # Extrae los datos del formulario enviado en la petición.
        nombre = request.form['nombre']
        email = request.form['email']
        comuna = int(request.form['comuna'])
        carrera = request.form['carrera_interes']

        # Valida que la comuna esté en el rango permitido.
        if not (1 <= comuna <= 16):
            return jsonify({"error": "La comuna debe estar entre 1 y 16."}), 400

        # Obtiene una conexión a la base de datos.
        conn = get_db_connection()
        if conn is None:
            return jsonify({"error": "No se pudo conectar a la base de datos."}), 500

        # Inserta el nuevo registro en la tabla 'usuarios'.
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO usuarios (nombre, email, comuna, carrera_interes) VALUES (%s, %s, %s, %s)",
            (nombre, email, comuna, carrera)
        )
        conn.commit()
        cur.close()
        
        # Devuelve una respuesta de éxito en formato JSON.
        return jsonify({"message": "¡Usuario registrado con éxito!"})

    except psycopg2.IntegrityError:
        # Error específico que ocurre si se viola una restricción (ej. email duplicado).
        return jsonify({"error": "El correo electrónico ya está registrado."}), 409
    except Exception as e:
        # Captura cualquier otro error durante el proceso.
        print(f"Error en /register: {e}")
        return jsonify({"error": "Ocurrió un error al procesar el registro.", "details": str(e)}), 500
    finally:
        # Asegura que la conexión a la base de datos se cierre siempre.
        if conn:
            conn.close()

if __name__ == '__main__':
    # Este bloque se ejecuta solo si el script se corre directamente.
    # En producción, un servidor WSGI como Gunicorn se encargará de ejecutar la app.
    app.run(host='0.0.0.0', port=int(PORT), debug=True)