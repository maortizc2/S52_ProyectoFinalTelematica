# Informe Final de Proyecto: Arquitectura de Microservicios y Despliegue Automatizado

## 1. Resumen del Proyecto

Este documento detalla la arquitectura y el proceso de despliegue de una aplicación web de registro de usuarios. El sistema se ha diseñado siguiendo un enfoque de microservicios, se ha contenerizado con Docker y se ha desplegado en un clúster de Docker Swarm sobre infraestructura de AWS. El proceso completo, desde la construcción de las imágenes hasta el despliegue, está automatizado mediante un pipeline de CI/CD con GitHub Actions.

## 2. Diagrama de Arquitectura

A continuación, se presenta el diagrama de la arquitectura final en producción:

```mermaid
graph TD
    subgraph "Internet"
        Usuario[Usuario]
    end

    subgraph "AWS Cloud"
        subgraph "VPC"
            subgraph "Nodo Manager (EC2)"
                A[Traefik <br><i>Edge Router</i>]
            end
            
            subgraph "Nodo Frontend (EC2)"
                W1[WebApp (EN) <br><i>Contenedor</i>]
                W2[WebApp (ES) <br><i>Contenedor</i>]
            end

            subgraph "Nodo Database (EC2)"
                DB[(PostgreSQL <br><i>Contenedor</i>)]
            end

            subgraph "Nodo Processing (EC2)"
                S[Stats App <br><i>Contenedor</i>]
            end

            Usuario -- HTTPS (puerto 443) --> A
            A -- Round-Robin --> W1
            A -- Round-Robin --> W2
            W1 -- TCP --> DB
            W2 -- TCP --> DB
            S -- TCP --> DB
        end
    end

    subgraph "Servicios Externos"
        Email[Servicio de Email <br><i>(AWS SES / Mailtrap)</i>]
        DNS[DNS Provider <br><i>(Freenom)</i>]
    end

    S -- API Call --> Email
    Usuario -- DNS Query --> DNS
    DNS -- IP del Manager --> Usuario
```

## 3. Pila Tecnológica (Stack)

*   **AWS (Amazon Web Services):** Proveedor de nube para la infraestructura (EC2, Security Groups, SES).
*   **Docker:** Plataforma de contenerización para empaquetar y aislar las aplicaciones y sus dependencias.
*   **Docker Swarm:** Orquestador de contenedores nativo de Docker para gestionar el clúster y el ciclo de vida de los servicios.
*   **Docker Compose:** Herramienta para definir y ejecutar aplicaciones Docker multi-contenedor en un entorno de desarrollo local.
*   **Traefik:** Edge router moderno que gestiona el tráfico de entrada, el balanceo de carga y la generación automática de certificados SSL/TLS.
*   **PostgreSQL:** Sistema de gestión de bases de datos relacional, robusto y de código abierto.
*   **Freenom:** Proveedor de nombres de dominio utilizado para apuntar un dominio público a la aplicación.
*   **GitHub Actions:** Plataforma de CI/CD integrada en GitHub para automatizar los flujos de trabajo de construcción y despliegue.
*   **Python (Flask/FastAPI):** Lenguaje y frameworks utilizados para desarrollar las aplicaciones web y el balanceador de carga inicial.
*   **Matplotlib:** Librería para la generación de gráficos y visualizaciones en Python.
*   **Gunicorn / Uvicorn:** Servidores WSGI/ASGI de nivel de producción para ejecutar las aplicaciones Python.

## 4. Estructura del Repositorio

El repositorio está organizado de la siguiente manera:

- **`.github/workflows/`**: Contiene los pipelines de CI/CD.
- **`docs/`**: Documentación del proyecto.
- **`infra/`**: Scripts para la gestión de la infraestructura (inicialización de BD y de EC2).
- **`load_balancer/`**: Código fuente del balanceador de carga (reemplazado por Traefik en producción).
- **`stats_app/`**: Código fuente del microservicio de estadísticas.
- **`web_app/`**: Código fuente de la aplicación web de registro.
- **`docker-compose.yml`**: Orquestación para el entorno de desarrollo local.
- **`docker-stack.yml`**: Orquestación para el despliegue en producción (Swarm).
- **`deploy.sh`**: Script para automatizar el despliegue en el clúster de Swarm.

## 5. Procedimientos

### 5.1. Ejecución en Local

1.  Crear y configurar el archivo `.env` a partir de `.env.example`.
2.  Ejecutar `docker-compose up --build -d`.
3.  Poblar la base de datos con `docker-compose exec stats python infra/seed_db.py`.
4.  Acceder a la aplicación en `http://localhost`.

### 5.2. Despliegue en Producción (AWS)

1.  **Infraestructura:** Seguir los pasos del `Paso 3` de la guía para crear la infraestructura en AWS (VPC, Security Group, EC2, etc.).
2.  **CI (Integración Continua):** Hacer `push` a la rama `main`. GitHub Actions construirá y publicará las imágenes Docker en Docker Hub.
3.  **CD (Despliegue Continuo):**
    *   Configurar el DNS para que el dominio apunte a la IP del nodo manager.
    *   Actualizar los placeholders en `docker-stack.yml` (dominio y email).
    *   Ejecutar el script `./deploy.sh <IP_DEL_MANAGER>`.
4.  La aplicación estará disponible en `https://<TU_DOMINIO>`.

## 6. Consideraciones de Seguridad

- **Gestión de Secretos:** Las contraseñas y claves de API se gestionan con Docker Secrets en producción y con un archivo `.env` (excluido por `.gitignore`) en desarrollo.
- **Redes:** La base de datos no está expuesta a internet. La comunicación entre servicios se realiza a través de una red `overlay` privada de Docker.
- **HTTPS:** Todo el tráfico web está cifrado mediante SSL/TLS con certificados de Let's Encrypt gestionados automáticamente por Traefik.
- **Principio de Menor Privilegio:** Los contenedores se ejecutan con usuarios no-root. Las reglas de firewall (Security Group) solo exponen los puertos estrictamente necesarios (80, 443, 22).