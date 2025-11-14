# Proyecto: Despliegue Docker + Swarm en AWS (Web en EN/ES, LB Round-Robin, Postgres, Stats+Email)

## Resumen
Este repositorio contiene 3 servicios:
- web_app (Flask) — dos instancias: LANG=en (web1), LANG=es (web2)
- load_balancer (FastAPI) — proxy reverso con round-robin y backoff
- stats_app (Flask) — genera gráficas y envía email
- db (Postgres)

## Cómo ejecutar local (rápido)
1. Construir imágenes:
docker build -t myuser/web_app:latest ./web_app
docker build -t myuser/stats_app:latest ./stats_app
docker build -t myuser/load_balancer:latest ./load_balancer

2. Levantar con Compose:
docker compose up -d

3. Abrir en el navegador: http://localhost

## Despliegue en AWS (resumen)
1. Crear 4 EC2 (init-ec2.sh como user-data).
2. Instalar Docker (script incluido).
3. Inicializar Swarm en nodo1, unir nodos con token.
4. Etiquetar nodos (`docker node update --label-add role=...`).
5. Crear secret DB (`echo "apppass" | docker secret create db_pass -`).
6. Desplegar stack desde manager:
 docker stack deploy -c docker-stack.yml mystack

## Seguridad
- Usar secretos (Docker secrets, AWS Secrets Manager).
- No exponer Postgres públicamente.
- Habilitar HTTPS (Let's Encrypt + reverse proxy) en balanceador.

## CI/CD
Config en `.github/workflows/docker-publish.yml` — setear `DOCKERHUB_USERNAME` y `DOCKERHUB_TOKEN` en GitHub Secrets.

