#!/usr/bin/env bash
# ==============================================================================
# RepoArchaeology - Instalador Nativo para Linux con Descarga de Modelo IA
# ==============================================================================
set -euo pipefail

BOLD="\033[1m"
GREEN="\033[32m"
BLUE="\033[34m"
YELLOW="\033[33m"
CYAN="\033[36m"
RED="\033[31m"
RESET="\033[0m"

APP_NAME="repoarchaeology"
BIN_NAME="repoarch"
INSTALL_DIR="${HOME}/.local/share/${APP_NAME}"
BIN_DIR="${HOME}/.local/bin"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_AI_MODEL="qwen2.5-coder:1.5b"

echo -e "${BOLD}${BLUE}"
echo "  ___                  _          _                  _                 "
echo " | _ \___ _ __  ___   /_\  _ _ __| |_  __ _ ___ ___ | |___  __ _ _  _ "
echo " |   / -_) '_ \/ _ \ / _ \| '_/ _| ' \/ _\` / -_) _ \| / _ \/ _\` | || |"
echo " |_|_\___| .__/\___//_/ \_\_| \__|_||_\__,_\___\___/|_\___/\__, |\_, |"
echo "         |_|                                               |___/ |__/ "
echo -e "${RESET}"
echo -e "${BOLD}Instalador Nativo de RepoArchaeology para Linux${RESET}\n"

# 1. Verificar Python 3.10+ y Git
echo -e "${BLUE}[1/6] Verificando dependencias del sistema...${RESET}"
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

if ! command -v git &>/dev/null; then
    echo -e "${RED}Error: git no está instalado.${RESET}"
    exit 1
fi
echo -e "  ${GREEN}✓ Git detectado.${RESET}"

# 2. Crear entorno virtual aislado
echo -e "\n${BLUE}[2/6] Creando entorno aislado en ${INSTALL_DIR}...${RESET}"
mkdir -p "${INSTALL_DIR}"
python3 -m venv "${INSTALL_DIR}/venv"

# 3. Instalar dependencias con salida limpia (sin spam de líneas)
echo -e "\n${BLUE}[3/6] Instalando dependencias completas de RepoArchaeology...${RESET}"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip --quiet --no-color
"${INSTALL_DIR}/venv/bin/pip" install --quiet --no-color -e "${PROJECT_DIR}[tui,ai]"
echo -e "  ${GREEN}✓ Paquete y dependencias instalados correctamente.${RESET}"

# 4. Configurar e inicializar Modelo de IA Ligero y Optimizado
echo -e "\n${BLUE}[4/6] Configurando Motor de Inteligencia Artificial Local...${RESET}"
AI_CONFIGURED="offline"

if command -v ollama &>/dev/null; then
    echo -e "  ${GREEN}✓ Ollama detectado en el sistema.${RESET}"
    
    # Comprobar si el servicio ollama está corriendo
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        echo -e "  ${CYAN}Verificando/Descargando modelo optimizado: ${BOLD}${DEFAULT_AI_MODEL}${RESET} (~980MB, alta velocidad)..."
        # Descarga con salida limpia
        if ollama pull "${DEFAULT_AI_MODEL}"; then
            echo -e "  ${GREEN}✓ Modelo ${DEFAULT_AI_MODEL} listo y disponible.${RESET}"
            AI_CONFIGURED="local"
        else
            echo -e "  ${YELLOW}Aviso: No se pudo descargar el modelo de Ollama. Se usará el motor heurístico local.${RESET}"
        fi
    else
        echo -e "  ${YELLOW}El servicio Ollama no está activo en http://localhost:11434.${RESET}"
        echo -e "  ${CYAN}Para activarlo más adelante: 'ollama serve' y 'ollama pull ${DEFAULT_AI_MODEL}'.${RESET}"
    fi
else
    echo -e "  ${YELLOW}Ollama no está instalado.${RESET}"
    echo -e "  ${CYAN}RepoArchaeology funcionará al 100% con su motor determinista offline integrado (cero dependencias externas).${RESET}"
fi

# 5. Generar archivo .env local y global
echo -e "\n${BLUE}[5/6] Configurando variables de entorno (.env)...${RESET}"

# Global .env
cat << EOF > "${INSTALL_DIR}/.env"
# Configuración global generada por install.sh
AI_PROVIDER=${AI_CONFIGURED}
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=${DEFAULT_AI_MODEL}
MAX_COMMITS_SCAN=500
ANALYZE_MAX_FILE_SIZE_KB=1024
EOF
echo -e "  ${GREEN}✓ Configuración global creada en ${INSTALL_DIR}/.env${RESET}"

# Local .env en el proyecto si no existe
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    if [ -f "${PROJECT_DIR}/.env.example" ]; then
        cp "${PROJECT_DIR}/.env.example" "${PROJECT_DIR}/.env"
        # Ajustar el provider por defecto detectado
        sed -i "s/AI_PROVIDER=.*/AI_PROVIDER=${AI_CONFIGURED}/" "${PROJECT_DIR}/.env" 2>/dev/null || true
    else
        cp "${INSTALL_DIR}/.env" "${PROJECT_DIR}/.env"
    fi
    echo -e "  ${GREEN}✓ Configuración local creada en ${PROJECT_DIR}/.env${RESET}"
else
    echo -e "  ${GREEN}✓ Archivo .env local ya existente respetado.${RESET}"
fi

# 6. Crear ejecutables en ~/.local/bin
echo -e "\n${BLUE}[6/6] Creando comandos globales en ${BIN_DIR}...${RESET}"
mkdir -p "${BIN_DIR}"

WRAPPER_SCRIPT="${BIN_DIR}/${BIN_NAME}"
cat << 'EOF' > "${WRAPPER_SCRIPT}"
#!/usr/bin/env bash
INSTALL_DIR="${HOME}/.local/share/repoarchaeology"
if [ -f "${INSTALL_DIR}/.env" ]; then
    export $(grep -v '^#' "${INSTALL_DIR}/.env" | xargs) 2>/dev/null || true
fi
exec "${INSTALL_DIR}/venv/bin/python" -m repoarchaeology.cli.entrypoint "$@"
EOF
chmod +x "${WRAPPER_SCRIPT}"

# Enlace adicional como repoarchaeology
ln -sf "${WRAPPER_SCRIPT}" "${BIN_DIR}/${APP_NAME}"
echo -e "  ${GREEN}✓ Comandos creados: '${BIN_NAME}' y '${APP_NAME}'.${RESET}"

# Verificación de PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "\n${YELLOW}Aviso: '${BIN_DIR}' no está en tu variable PATH actual.${RESET}"
    echo -e "Añade esta línea a tu ~/.bashrc o ~/.zshrc:"
    echo -e "${BOLD}  export PATH="\$HOME/.local/bin:\$PATH"${RESET}\n"
fi

echo -e "${BOLD}${GREEN}========================================================================${RESET}"
echo -e "${BOLD}${GREEN} ¡Instalación de RepoArchaeology completada con éxito!${RESET}"
echo -e "${BOLD}${GREEN}========================================================================${RESET}"
echo -e "Modo de Inteligencia Artificial activo: ${BOLD}${CYAN}${AI_CONFIGURED}${RESET}"
echo -e "Comandos listos para usar:"
echo -e "  ${BOLD}${BLUE}repoarch doctor${RESET}     -> Diagnóstico completo de salud y bus factor"
echo -e "  ${BOLD}${BLUE}repoarch churn${RESET}      -> Hotspots y código frágil con mayor rotación"
echo -e "  ${BOLD}${BLUE}repoarch coupling${RESET}   -> Detección de acoplamientos invisibles/fantasma"
echo -e "  ${BOLD}${BLUE}repoarch breaking${RESET}   -> Detección de cambios de contrato entre ramas"
echo -e "  ${BOLD}${BLUE}repoarch update${RESET}     -> Actualizar RepoArchaeology a la última versión"
echo -e "  ${BOLD}${BLUE}repoarch --help${RESET}     -> Ver el manual completo\n"
