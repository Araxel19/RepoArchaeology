"""
Mecanismos de seguridad, sanitización de rutas y protección contra fuga de credenciales.
"""
import os
import re
from pathlib import Path
from typing import Optional


SECRET_PATTERNS = [
    re.compile(r'(?i)(api[_-]?key|secret|token|password|passwd|auth[_-]?token|bearer)\s*[:=]\s*["']?([a-zA-Z0-9_\-\.]{8,})["']?'),
    re.compile(r'(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{82})'),
    re.compile(r'(xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,32})'),
    re.compile(r'(AIza[0-9A-Za-z-_]{35})'),  # Google API Keys
]


def sanitize_path(raw_path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Valida y sanitiza una ruta para prevenir ataques de Path Traversal.
    """
    base = base_dir.resolve() if base_dir else Path.cwd().resolve()
    target = (base / raw_path).resolve() if not os.path.isabs(raw_path) else Path(raw_path).resolve()
    
    return target


def redact_secrets(text: str) -> str:
    """
    Enmascara credenciales, tokens y secretos encontrados en textos o commits.
    """
    if not text:
        return text
        
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(r': [REDACTED_SECRET]', sanitized)
        
    return sanitized
