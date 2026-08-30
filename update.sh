#!/usr/bin/env bash
# ==============================================================================
# RepoArchaeology - Script de Actualización Rápida
# ==============================================================================
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
BLUE="\033[34m"
CYAN="\033[36m"
YELLOW="\033[33m"
RESET="\033[0m"

APP_NAME="repoarchaeology"
INSTALL_DIR="${HOME}/.local/share/${APP_NAME}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BOLD}${BLUE}Actualizando RepoArchaeology...${RESET}\n"

# 1. Sincronizar repositorio Git
echo -e "${CYAN}[1/3] Descargando últimos cambios de Git...${RESET}"
cd "${PROJECT_DIR}"
git pull --quiet
echo -e "  ${GREEN}✓ Código fuente sincronizado.${RESET}"

# 2. Actualizar entorno virtual
echo -e "\n${CYAN}[2/3] Actualizando dependencias en el entorno aislado...${RESET}"
if [ -d "${INSTALL_DIR}/venv" ]; then
    "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip --quiet --no-color
    "${INSTALL_DIR}/venv/bin/pip" install --quiet --no-color -e ".[tui,ai]"
    echo -e "  ${GREEN}✓ Dependencias y paquete actualizados.${RESET}"
else
    echo -e "  ${YELLOW}No se encontró el entorno virtual. Ejecuta ./install.sh para crearlo.${RESET}"
fi

# 3. Sincronizar archivo .env
echo -e "\n${CYAN}[3/3] Sincronizando configuración de entorno (.env)...${RESET}"
if [ ! -f "${PROJECT_DIR}/.env" ] && [ -f "${PROJECT_DIR}/.env.example" ]; then
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
    echo -e "  ${GREEN}✓ Creado .env local desde .env.example.${RESET}"
fi

echo -e "\n${BOLD}${GREEN}========================================================================${RESET}"
echo -e "${BOLD}${GREEN} ¡RepoArchaeology ha sido actualizado con éxito!${RESET}"
echo -e "${BOLD}${GREEN}========================================================================${RESET}\n"
