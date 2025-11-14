import os
import psycopg2
from psycopg2 import sql
from faker import Faker
import random
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# --- Configuración ---
# Lee la URL de conexión a la base de datos desde las variables de entorno
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/mydatabase")
NUM_RECORDS = 50  # Número de registros falsos a generar

# --- Inicialización ---
fake = Faker()

# Carreras y comunas posibles
carreras = ["Medicina", "Ingeniería", "Abogacía", "Licenciatura", "Arquitectura"]
comunas = list(range(1, 11))

def seed_database():
    """
    Conecta a la base de datos PostgreSQL y la puebla con datos generados por Faker.
    """
    conn = None
    try:
        # Conectar a la base de datos
        print(f"Conectando a la base de datos...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        print("Conexión exitosa.")

        # Insertar registros
        print(f"Insertando {NUM_RECORDS} registros falsos...")
        for i in range(NUM_RECORDS):
            name = fake.name()
            comuna = random.choice(comunas)
            carrera = random.choice(carreras)
            lang = random.choice(['en', 'es'])
            
            cur.execute(
                sql.SQL("INSERT INTO users (name, comuna, carrera, lang) VALUES (%s, %s, %s, %s)"),
                (name, comuna, carrera, lang)
            )
            if (i + 1) % 10 == 0:
                print(f"  ... {i + 1}/{NUM_RECORDS} registros insertados.")

        # Confirmar los cambios
        conn.commit()
        print("¡Inserción completada y cambios confirmados!")

    except psycopg2.OperationalError as e:
        print(f"Error de conexión: No se pudo conectar a la base de datos.")
        print(f"Detalle: {e}")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        if conn:
            conn.rollback() # Revertir cambios en caso de error
    finally:
        # Cerrar la conexión
        if cur:
            cur.close()
        if conn:
            conn.close()
            print("Conexión cerrada.")

if __name__ == "__main__":
    seed_database()