#!/usr/bin/env bash
# ==============================================================================
# RepoArchaeology - Desinstalador Limpio para Linux
# ==============================================================================
set -euo pipefail

APP_NAME="repoarchaeology"
BIN_NAME="repoarch"
INSTALL_DIR="${HOME}/.local/share/${APP_NAME}"
BIN_DIR="${HOME}/.local/bin"

echo "Desinstalando RepoArchaeology..."

rm -rf "${INSTALL_DIR}"
rm -f "${BIN_DIR}/${BIN_NAME}"
rm -f "${BIN_DIR}/${APP_NAME}"

echo "RepoArchaeology ha sido desinstalado de tu sistema."
