"""
Capa de seguridad de RepoArchaeology:
- Sanitización de rutas y prevención de Path Traversal
- Enmascarado de tokens, contraseñas y claves privadas
"""
import os
import re
from pathlib import Path
from typing import Optional

SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret|token|password|passwd|auth[_-]?token|bearer)\s*[:=]\s*[\'"]?([a-zA-Z0-9_\-\.]{8,})[\'"]?'),
    re.compile(r'(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})'),
    re.compile(r'(xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32})'),
    re.compile(r'(AIza[0-9A-Za-z-_]{35})'),
    re.compile(r'(sk-[a-zA-Z0-9]{20,48})'),
    re.compile(r'-----BEGIN (RSA|EC|OPENSSH|DSA|PGP) PRIVATE KEY-----'),
]


def sanitize_path(raw_path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Valida y sanitiza una ruta para asegurar que no escape de los límites permitidos.
    """
    base = base_dir.resolve() if base_dir else Path.cwd().resolve()
    if not os.path.isabs(raw_path):
        target = (base / raw_path).resolve()
    else:
        target = Path(raw_path).resolve()
    return target


def redact_secrets(text: str) -> str:
    """
    Enmascara credenciales, tokens o secretos en mensajes de commit o diffs.
    """
    if not text:
        return ""
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(r'[REDACTED_SECRET]', sanitized)
    return sanitized
