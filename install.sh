#!/usr/bin/env bash
# ==============================================================================
# RepoArchaeology - Instalador Nativo para Linux
# ==============================================================================
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
BLUE="\033[34m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

APP_NAME="repoarchaeology"
BIN_NAME="repoarch"
INSTALL_DIR="${HOME}/.local/share/${APP_NAME}"
BIN_DIR="${HOME}/.local/bin"

echo -e "${BOLD}${BLUE}"
echo "  ___                  _          _                  _                 "
echo " | _ \___ _ __  ___   /_\  _ _ __| |_  __ _ ___ ___ | |___  __ _ _  _ "
echo " |   / -_) '_ \/ _ \ / _ \| '_/ _| ' \/ _\` / -_) _ \| / _ \/ _\` | || |"
echo " |_|_\___| .__/\___//_/ \_\_| \__|_||_\__,_\___\___/|_\___/\__, |\_, |"
echo "         |_|                                               |___/ |__/ "
echo -e "${RESET}"
echo -e "${BOLD}Instalador Nativo de RepoArchaeology para Linux${RESET}\n"

# 1. Verificar Python 3.10+
echo -e "${BLUE}[1/5] Verificando dependencias del sistema...${RESET}"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 no está instalado. Por favor instálalo primero.${RESET}"
    exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || [ "$PY_MINOR" -lt 10 ]; then
    echo -e "${RED}Error: Se requiere Python 3.10 o superior (Detectado: $PY_VERSION).${RESET}"
    exit 1
fi
echo -e "  ${GREEN}✓ Python $PY_VERSION detectado.${RESET}"

# 2. Verificar Git
if ! command -v git &>/dev/null; then
    echo -e "${RED}Error: git no está instalado.${RESET}"
    exit 1
fi
echo -e "  ${GREEN}✓ Git detectado.${RESET}"

# 3. Crear entorno virtual aislado
echo -e "\n${BLUE}[2/5] Creando entorno aislado en ${INSTALL_DIR}...${RESET}"
mkdir -p "${INSTALL_DIR}"
python3 -m venv "${INSTALL_DIR}/venv"

# 4. Instalar dependencias y paquete
echo -e "\n${BLUE}[3/5] Instalando dependencias de RepoArchaeology...${RESET}"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip --quiet
"${INSTALL_DIR}/venv/bin/pip" install -e . --quiet
echo -e "  ${GREEN}✓ Paquete instalado exitosamente en el entorno virtual.${RESET}"

# 5. Crear ejecutable en ~/.local/bin
echo -e "\n${BLUE}[4/5] Creando accesos directos en ${BIN_DIR}...${RESET}"
mkdir -p "${BIN_DIR}"

WRAPPER_SCRIPT="${BIN_DIR}/${BIN_NAME}"
cat << 'EOF' > "${WRAPPER_SCRIPT}"
#!/usr/bin/env bash
INSTALL_DIR="${HOME}/.local/share/repoarchaeology"
exec "${INSTALL_DIR}/venv/bin/python" -m repoarchaeology.cli.entrypoint "$@"
EOF
chmod +x "${WRAPPER_SCRIPT}"

# Enlace adicional como repoarchaeology
ln -sf "${WRAPPER_SCRIPT}" "${BIN_DIR}/${APP_NAME}"

echo -e "  ${GREEN}✓ Comandos creados: '${BIN_NAME}' y '${APP_NAME}'.${RESET}"

# 6. Comprobación de PATH
echo -e "\n${BLUE}[5/5] Verificando variable PATH...${RESET}"
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${YELLOW}Aviso: '${BIN_DIR}' no parece estar en tu variable PATH.${RESET}"
    echo -e "Para usar '${BIN_NAME}' directamente, añade esta línea a tu ~/.bashrc o ~/.zshrc:"
    echo -e "${BOLD}  export PATH="\$HOME/.local/bin:\$PATH"${RESET}\n"
fi

echo -e "${BOLD}${GREEN}========================================================================${RESET}"
echo -e "${BOLD}${GREEN} ¡Instalación completada con éxito!${RESET}"
echo -e "${BOLD}${GREEN}========================================================================${RESET}"
echo -e "Para comenzar a usarlo, entra a cualquier repositorio Git y escribe:"
echo -e "  ${BOLD}${BLUE}repoarch doctor${RESET}   -> Para un diagnóstico general de salud."
echo -e "  ${BOLD}${BLUE}repoarch churn${RESET}    -> Para encontrar los archivos más calientes."
echo -e "  ${BOLD}${BLUE}repoarch --help${RESET}   -> Para ver todas las opciones disponibles.\n"
