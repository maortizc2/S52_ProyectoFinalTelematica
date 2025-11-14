#!/bin/bash
# Script de inicialización (user-data) para instancias EC2 basadas en Ubuntu

# Actualizar los paquetes del sistema
apt-get update -y
apt-get upgrade -y

# Instalar paquetes necesarios para añadir repositorios y para Docker
apt-get install -y apt-transport-https ca-certificates curl software-properties-common

# Añadir la clave GPG oficial de Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

# Añadir el repositorio de Docker a las fuentes de APT
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Actualizar la base de datos de paquetes con los paquetes de Docker del nuevo repo
apt-get update -y

# Instalar la última versión de Docker CE (Community Edition)
apt-get install -y docker-ce

# Añadir el usuario 'ubuntu' al grupo 'docker'
# Esto permite ejecutar comandos de Docker sin necesidad de 'sudo'
usermod -aG docker ubuntu

# Habilitar el servicio de Docker para que se inicie en cada arranque
systemctl enable docker

echo "¡Instalación de Docker completada y configurada!"
