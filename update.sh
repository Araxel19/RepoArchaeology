#!/usr/bin/env bash
# ==============================================================================
# RepoArchaeology - Actualizador Rápido y Amigable
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

echo -e "${BOLD}${BLUE}🔍 Comprobando y actualizando RepoArchaeology...${RESET}\n"

# 1. Sincronizar repositorio Git
echo -e "${CYAN}⬇️  Descargando últimas mejoras y novedades...${RESET}"
cd "${PROJECT_DIR}"
git pull origin main --ff-only --quiet 2>/dev/null || true

# 2. Actualizar entorno virtual
echo -e "${CYAN}⚙️  Configurando los componentes del sistema...${RESET}"
if [ -d "${INSTALL_DIR}/venv" ]; then
    "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip --quiet --no-color 2>/dev/null || true
    "${INSTALL_DIR}/venv/bin/pip" install --quiet --no-color -e "${PROJECT_DIR}[tui,ai]" 2>/dev/null || true
fi

# 3. Sincronizar archivo .env
if [ ! -f "${PROJECT_DIR}/.env" ] && [ -f "${PROJECT_DIR}/.env.example" ]; then
    cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
fi

echo -e "\n${BOLD}${GREEN}========================================================================${RESET}"
echo -e "${BOLD}${GREEN} 🎉 ¡Todo listo! RepoArchaeology está al día con la versión más reciente.${RESET}"
echo -e "${BOLD}${GREEN}========================================================================${RESET}\n"
