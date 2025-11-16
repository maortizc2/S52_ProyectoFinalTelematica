# Proyecto de Arquitectura Web con Docker

Este proyecto implementa una arquitectura de microservicios completamente funcional y contenerizada utilizando Docker Compose. La solución incluye dos servidores web con balanceo de carga, una base de datos PostgreSQL y un servicio de estadísticas que genera reportes y los envía por correo electrónico.

## 📋 Arquitectura

El sistema está compuesto por los siguientes servicios orquestados por Docker Compose:

1.  **Load Balancer (`load-balancer`)**:
    *   Un proxy inverso basado en FastAPI que distribuye el tráfico entrante en el puerto `5050` entre los dos servidores web.
    *   Utiliza un algoritmo **Round-Robin** para alternar las peticiones.
    *   Actúa como el único punto de entrada a la aplicación web.

2.  **Servidor Web en Inglés (`web-server-en`)**:
    *   Una aplicación Flask que sirve la versión en **inglés** del formulario de registro de usuarios.
    *   Se conecta a la base de datos para guardar nuevos registros.

3.  **Servidor Web en Español (`web-server-es`)**:
    *   Una aplicación Flask idéntica a la anterior, pero configurada para servir la versión en **español** del formulario.

4.  **Aplicación de Estadísticas (`stats-app`)**:
    *   Un servicio Flask que se conecta a la base de datos para generar un gráfico de estadísticas de usuarios por carrera.
    *   Utiliza Matplotlib para la generación del gráfico.
    *   Envía el reporte a un correo electrónico predefinido a través de un servidor SMTP (Mailtrap).

5.  **Base de Datos (`db`)**:
    *   Un contenedor PostgreSQL que almacena todos los datos de la aplicación, principalmente la tabla `usuarios`.
    *   Los datos persisten en un volumen de Docker para evitar su pérdida al reiniciar los contenedores.

---

## ✨ Características

*   **Contenerización Completa**: Todos los servicios se ejecutan en contenedores Docker aislados.
*   **Orquestación Sencilla**: Toda la arquitectura se levanta con un solo comando (`docker compose up`).
*   **Balanceo de Carga**: Distribución de tráfico Round-Robin para alta disponibilidad y escalabilidad.
*   **Internacionalización (i18n)**: La aplicación web se sirve en dos idiomas diferentes.
*   **Base de Datos Relacional**: Uso de PostgreSQL para un almacenamiento de datos robusto.
*   **Generación de Reportes**: Un microservicio dedicado a tareas asíncronas como la generación de gráficos y el envío de correos.

---

## 🚀 Cómo Empezar

Sigue estos pasos para configurar y ejecutar el proyecto en tu máquina local.

### Requisitos Previos

*   [Docker](https://www.docker.com/get-started/)
*   [Docker Compose](https://docs.docker.com/compose/install/) (generalmente viene incluido con Docker Desktop)

### 1. Configuración del Entorno

1.  **Clona el repositorio** (si aún no lo has hecho).

2.  **Crea el archivo de entorno `.env`**:
    En la raíz del proyecto, crea una copia del archivo `.env.example` y nómbrala `.env`.

    ```bash
    # En Windows (PowerShell)
    cp .env.example .env

    # En Linux o macOS
    cp .env.example .env
    ```

3.  **Edita el archivo `.env`**:
    Abre el archivo `.env` y rellena tus credenciales de **Mailtrap.io**. Las demás variables ya están configuradas para funcionar localmente.

    ```ini
    # Rellena estos valores con tus credenciales de Mailtrap
    SMTP_USER=<TU_USUARIO_MAILTRAP>
    SMTP_PASS=<TU_PASSWORD_MAILTRAP>
    ```

### 2. Ejecutar la Aplicación

1.  Abre una terminal en la raíz del proyecto.
2.  Ejecuta el siguiente comando para construir las imágenes y levantar todos los servicios en segundo plano:

    ```bash
    docker compose up -d --build
    ```
    *   `up`: Inicia los servicios.
    *   `-d`: Modo "detached" (segundo plano).
    *   `--build`: Reconstruye las imágenes si ha habido cambios en el código o en los Dockerfiles.

### 3. Detener la Aplicación

Para detener todos los servicios, ejecuta:
```bash
docker compose down
```
Si además deseas eliminar los datos de la base de datos (almacenados en el volumen), usa:
```bash
docker compose down -v
```

---

## ⚙️ Cómo Usar la Aplicación

Una vez que los servicios estén en ejecución, puedes interactuar con ellos de la siguiente manera:

1.  **Aplicación Web**:
    *   Abre tu navegador y ve a **`http://localhost:5050`**.
    *   Verás el formulario de registro. Si recargas la página varias veces, notarás que el idioma cambia entre inglés y español gracias al balanceador de carga.
    *   Registra varios usuarios de prueba.

2.  **Servicio de Estadísticas**:
    *   **Ver el gráfico**: Para previsualizar el gráfico de estadísticas, ve a **`http://localhost:5001/stats/generate-chart`**.
    *   **Enviar el reporte**: Para generar el gráfico y enviarlo por correo, ve a **`http://localhost:5001/stats/send-report`**.
    *   **Verificar el correo**: Revisa tu bandeja de entrada en Mailtrap.io. Deberías tener un nuevo correo con el reporte adjunto.

### Resumen de Endpoints

| Servicio             | URL Local                               | Descripción                               |
| -------------------- | --------------------------------------- | ----------------------------------------- |
| **Aplicación Web**   | `http://localhost:5050`                 | Punto de entrada principal (con balanceo).|
| **Stats (Gráfico)**  | `http://localhost:5001/stats/generate-chart` | Visualiza el gráfico de estadísticas.     |
| **Stats (Reporte)**  | `http://localhost:5001/stats/send-report`    | Envía el reporte por correo.              |
| **Base de Datos**    | `localhost:5432`                        | Puerto para conexión con un cliente SQL.  |

---