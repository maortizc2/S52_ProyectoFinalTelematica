#!/bin/bash

# Script para desplegar la aplicación en un clúster de Docker Swarm
# Se ejecuta desde la máquina local del desarrollador.

# --- Configuración ---
# Termina el script si cualquier comando falla
set -e

# El nombre que le daremos a nuestro stack en Docker Swarm
STACK_NAME="my-app"

# --- Validaciones ---
# Verifica que se haya pasado la IP del manager como argumento
if [ -z "$1" ]; then
  echo "Error: Debes proporcionar la IP pública del nodo manager de Swarm."
  echo "Uso: ./deploy.sh <IP_PUBLICA_DEL_MANAGER>"
  exit 1
fi

# --- Variables (reemplaza con tus datos) ---
MANAGER_IP=$1
SSH_USER="ubuntu"
SSH_KEY="~/.ssh/<MI_CLAVE_SSH>.pem" # Reemplaza con la ruta a tu clave SSH
DOCKERHUB_USER="<TU_USUARIO_DOCKERHUB>" # Reemplaza con tu usuario de Docker Hub

# --- Pasos del Despliegue ---

echo "Paso 1: Copiando archivos de configuración al manager ($MANAGER_IP)..."
# Copia el archivo de stack y el archivo de entorno al home del usuario en el manager
scp -i $SSH_KEY docker-stack.yml $SSH_USER@$MANAGER_IP:~/docker-stack.yml
scp -i $SSH_KEY .env $SSH_USER@$MANAGER_IP:~/.env
echo "Archivos copiados."

echo "Paso 2: Conectando al manager y desplegando el stack..."
# Ejecuta los comandos de despliegue en el manager vía SSH
ssh -i $SSH_KEY $SSH_USER@$MANAGER_IP << EOF
  # Exportar las variables de entorno del archivo .env para que docker-stack las use
  export \$(grep -v '^#' .env | xargs)

  # Reemplazar el placeholder del usuario de Docker Hub en el stack file
  # Esto es importante para que Swarm sepa qué imágenes descargar
  sed -i "s/<TU_USUARIO_DOCKERHUB>/$DOCKERHUB_USER/g" docker-stack.yml

  echo "Iniciando sesión en Docker Hub en el manager..."
  # Es una buena práctica iniciar sesión en el manager antes de desplegar
  # El token se pasará a los workers con la bandera --with-registry-auth
  docker login -u "$DOCKERHUB_USER" -p "$DOCKERHUB_TOKEN" 
  # Nota: Se asume que DOCKERHUB_TOKEN es una variable de entorno en la máquina local
  # o se pega manualmente si se solicita. Para mayor seguridad, usa un agente SSH.

  echo "Desplegando el stack '$STACK_NAME'..."
  # Despliega el stack. Docker Swarm se encargará de todo.
  # --with-registry-auth envía las credenciales de login a los nodos worker
  # para que puedan descargar las imágenes.
  docker stack deploy -c docker-stack.yml --with-registry-auth $STACK_NAME

  echo "¡Despliegue completado!"
  echo "Verificando el estado de los servicios..."
  docker service ls
EOF

echo "Script finalizado. Los servicios pueden tardar unos minutos en estar todos disponibles."