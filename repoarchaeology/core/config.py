"""
Gestión centralizada de configuración con soporte para .env y fallback seguro.
"""
import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Configuración global de RepoArchaeology."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    # Motor de IA: 'offline', 'local' (Ollama), 'gemini', 'openai'
    ai_provider: str = Field(default="offline", description="Proveedor IA activo")
    gemini_api_key: Optional[str] = Field(default=None, description="API Key para Gemini")
    openai_api_key: Optional[str] = Field(default=None, description="API Key para OpenAI")
    ollama_host: str = Field(default="http://localhost:11434", description="Host de Ollama")
    ollama_model: str = Field(default="qwen2.5-coder:1.5b", description="Modelo local optimizado")
    
    # Límites y afinación
    max_commits_scan: int = Field(default=500, description="Límite de commits a analizar")
    analyze_max_file_size_kb: int = Field(default=1024, description="Tamaño máx de archivo (KB)")
    min_coupling_confidence: float = Field(default=0.5, description="Umbral mínimo de acoplamiento")
    
    exclude_dirs: List[str] = Field(
        default=[
            ".git", "node_modules", ".venv", "venv", "dist", "build",
            "__pycache__", ".dart_tool", "vendor", ".idea", ".vscode",
            ".gradle", "target", "bin", "obj"
        ],
        description="Directorios excluidos del análisis forense"
    )


def load_config() -> AppConfig:
    """Carga la configuración combinando variables de entorno y defaults seguros."""
    # Cargar también desde el share de la app si existe
    user_env = Path.home() / ".local" / "share" / "repoarchaeology" / ".env"
    if user_env.exists() and not Path(".env").exists():
        return AppConfig(_env_file=str(user_env))
    return AppConfig()
