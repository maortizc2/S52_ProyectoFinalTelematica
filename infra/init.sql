-- =================================================================
-- SCRIPT DE INICIALIZACIÓN DE LA BASE DE DATOS
-- =================================================================
-- Este script se ejecuta automáticamente cuando el contenedor de PostgreSQL
-- se inicia por primera vez. Define la estructura de la base de datos.
-- =================================================================

-- --- Creación de Tipos Enumerados (ENUM) ---
-- Define un tipo personalizado para la carrera de interés,
-- asegurando que solo los valores permitidos puedan ser insertados.
CREATE TYPE carrera_type AS ENUM (
    'Medicina',
    'Ingeniería',
    'Abogacía',
    'Licenciatura'
);

-- --- Creación de la Tabla de Usuarios ---
-- Almacena la información de los usuarios registrados a través de la aplicación web.
CREATE TABLE IF NOT EXISTS usuarios (
    -- ID único para cada usuario, se autoincrementa.
    id SERIAL PRIMARY KEY,
    
    -- Nombre completo del usuario.
    nombre VARCHAR(100) NOT NULL,
    
    -- Email del usuario, debe ser único.
    email VARCHAR(100) UNIQUE NOT NULL,
    
    -- Comuna de residencia, restringida a valores entre 1 y 10.
    comuna INTEGER NOT NULL CHECK (comuna >= 1 AND comuna <= 16),
    
    -- Carrera de interés, usando el tipo ENUM definido previamente.
    carrera_interes carrera_type NOT NULL,
    
    -- Fecha y hora del registro, se establece automáticamente.
    fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- --- Comentarios Adicionales ---
-- La tabla 'usuarios' es el corazón de la aplicación.
-- El uso de 'CHECK' y 'ENUM' ayuda a mantener la integridad de los datos.
-- La columna 'fecha_registro' es útil para la aplicación de estadísticas.
