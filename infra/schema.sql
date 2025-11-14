-- Define la estructura de la tabla para almacenar los registros de usuarios.
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    comuna INTEGER NOT NULL CHECK (comuna >= 1 AND comuna <= 10),
    carrera VARCHAR(50) NOT NULL,
    registration_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    lang VARCHAR(2) NOT NULL
);