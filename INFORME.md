# Informe de Despliegue: Arquitectura de Microservicios

**Fecha:** 16 de noviembre de 2025

---

## 1. Resumen Ejecutivo

Este documento detalla el proceso de configuración y despliegue de una arquitectura de microservicios web completamente funcional y contenerizada. El objetivo principal es establecer un entorno resiliente, escalable y fácilmente gestionable utilizando Docker y Docker Compose.

La solución implementada consiste en una aplicación web para el registro de usuarios, servida en dos idiomas (inglés y español), con un balanceador de carga para distribuir el tráfico, una base de datos persistente y un servicio de estadísticas asíncrono para la generación y envío de reportes.

## 2. Arquitectura de la Solución

La arquitectura se compone de cinco servicios principales que se comunican a través de una red privada de Docker, garantizando el aislamiento y la seguridad.

![Diagrama de Arquitectura (Conceptual)](https://i.imgur.com/rG3gA5g.png)
*(Nota: Este es un diagrama conceptual representativo)*

#### 2.1. Balanceador de Carga (`load-balancer`)
- **Tecnología**: FastAPI (Python).
- **Función**: Actúa como el único punto de entrada a la aplicación (`Reverse Proxy`). Recibe todas las peticiones HTTP en el puerto `5050` y las distribuye a los servidores web disponibles.
- **Algoritmo**: Implementa un balanceo de carga **Round-Robin**, enviando cada nueva petición al siguiente servidor de la lista de forma secuencial. Esto distribuye la carga de manera equitativa.
- **Configuración**: Se configura mediante la variable de entorno `BACKEND_SERVERS` en el archivo `docker-compose.yml`, lo que permite añadir o quitar servidores web de forma flexible.

#### 2.2. Servidores Web (`web-server-en` y `web-server-es`)
- **Tecnología**: Flask (Python).
- **Función**: Sirven la aplicación web principal, que consiste en un formulario de registro. Cada instancia está configurada para un idioma específico a través de la variable de entorno `LANG`.
- **Internacionalización (i18n)**: `web-server-en` sirve la versión en inglés, mientras que `web-server-es` sirve la versión en español.
- **Conectividad**: Ambos servidores se conectan a la base de datos PostgreSQL para persistir la información de los usuarios registrados.

#### 2.3. Aplicación de Estadísticas (`stats-app`)
- **Tecnología**: Flask, Pandas, Matplotlib (Python).
- **Función**: Es un servicio desacoplado cuya responsabilidad es realizar tareas que pueden ser pesadas o lentas, sin afectar el rendimiento de la aplicación principal.
- **Generación de Gráficos**: Consulta la base de datos, procesa los datos con Pandas y genera un gráfico de barras con Matplotlib que muestra el número de usuarios registrados por carrera.
- **Envío de Reportes**: Envía el gráfico generado por correo electrónico a un destinatario predefinido, utilizando un servidor SMTP externo configurado (Mailtrap para pruebas).

#### 2.4. Base de Datos (`db`)
- **Tecnología**: PostgreSQL 14.
- **Función**: Proporciona persistencia de datos para toda la arquitectura. Almacena la información de los usuarios en la tabla `usuarios`.
- **Inicialización**: Al arrancar por primera vez, ejecuta el script `infra/init.sql` para crear la estructura de la base de datos, incluyendo la tabla `usuarios` y el tipo `carrera_type`.
- **Persistencia**: Utiliza un volumen nombrado de Docker (`postgres_data`) para asegurar que los datos no se pierdan aunque los contenedores se detengan o se eliminen.

## 3. Proceso de Configuración y Despliegue

A continuación, se describen los pasos necesarios para desplegar esta arquitectura en cualquier máquina con Docker.

### 3.1. Requisitos Previos
- **Docker Engine**: Instalado y en ejecución.
- **Docker Compose**: Instalado (generalmente incluido en Docker Desktop).

### 3.2. Configuración de Variables de Entorno
La configuración de la aplicación se gestiona a través de variables de entorno para mantener la portabilidad y la seguridad.

1.  **Creación del archivo `.env`**: Se debe crear un archivo `.env` en la raíz del proyecto a partir de la plantilla `.env.example`.
2.  **Variables Clave**:
    *   `POSTGRES_*`: Credenciales para la base de datos PostgreSQL.
    *   `DATABASE_URL`: La URL de conexión completa que usan las aplicaciones para conectarse a la base de datos. El host `db` es resuelto por la red interna de Docker.
    *   `SMTP_*`: Credenciales del servidor de correo para el envío de reportes. **Es fundamental que el usuario proporcione sus credenciales de Mailtrap en estas variables.**
    *   `RECIPIENT_EMAIL`: Dirección de correo que recibirá los reportes de estadísticas.

### 3.3. Orquestación con Docker Compose
El archivo `docker-compose.yml` es el núcleo del despliegue. Define todos los servicios, sus configuraciones, dependencias, redes y volúmenes.

- **Dependencias (`depends_on`)**: Se utilizan para controlar el orden de arranque. Los servidores web y la app de estadísticas solo se inician cuando la base de datos está saludable (`service_healthy`). El balanceador de carga, a su vez, espera a que los servidores web estén listos.
- **Healthchecks**: Se implementan verificaciones de estado para asegurar que los servicios dependientes solo se inicien cuando sus dependencias estén realmente operativas.

### 3.4. Comando de Despliegue
El despliegue completo se realiza con un único comando desde la raíz del proyecto:

```bash
docker compose up -d --build
```
- **`--build`**: Fuerza la reconstrucción de las imágenes de Docker, asegurando que cualquier cambio en el código fuente o en los `Dockerfiles` sea aplicado.
- **`-d`**: Ejecuta los contenedores en modo "detached" (en segundo plano).

## 4. Verificación del Despliegue

Para verificar que todos los componentes funcionan correctamente, se deben seguir los siguientes pasos:

1.  **Verificar Contenedores**: Ejecutar `docker compose ps` para asegurarse de que todos los contenedores están en estado `running` o `healthy`.
2.  **Probar Balanceo de Carga**: Acceder a `http://localhost:5050` y recargar la página varias veces. El idioma de la interfaz debe alternar entre inglés y español.
3.  **Probar Registro de Usuarios**: Completar y enviar el formulario en la página web. Se debe recibir un mensaje de confirmación.
4.  **Probar Servicio de Estadísticas**:
    *   Acceder a `http://localhost:5001/stats/generate-chart` para visualizar el gráfico.
    *   Acceder a `http://localhost:5001/stats/send-report` para disparar el envío del correo.
    *   Confirmar la recepción del correo en la bandeja de entrada de Mailtrap.

## 5. Conclusión

La arquitectura implementada proporciona una base sólida, escalable y fácil de mantener para la aplicación. El uso de Docker y Docker Compose simplifica drásticamente el proceso de despliegue, garantizando la consistencia del entorno desde el desarrollo local hasta un posible despliegue en producción en la nube. La separación de responsabilidades en microservicios mejora la resiliencia y permite el desarrollo y escalado independiente de cada componente.