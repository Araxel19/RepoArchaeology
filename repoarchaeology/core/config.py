"""
Gestión centralizada de configuración y variables de entorno.
"""
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Configuración global de la aplicación."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    ai_provider: str = Field(default="offline", description="Proveedor IA: offline, local, gemini, openai")
    gemini_api_key: Optional[str] = Field(default=None, description="API Key para Google Gemini")
    openai_api_key: Optional[str] = Field(default=None, description="API Key para OpenAI")
    ollama_host: str = Field(default="http://localhost:11434", description="Host de servidor Ollama")
    ollama_model: str = Field(default="qwen2.5-coder:7b", description="Modelo local para Ollama")
    
    max_commits_scan: int = Field(default=500, description="Límite de commits a analizar por defecto")
    analyze_max_file_size_kb: int = Field(default=1024, description="Tamaño máximo de archivo a parsear (KB)")
    
    exclude_dirs: List[str] = Field(
        default=[
            ".git", "node_modules", ".venv", "venv", "dist", "build",
            "__pycache__", ".dart_tool", "vendor", ".idea", ".vscode"
        ],
        description="Directorios excluidos del análisis forense"
    )


def load_config() -> AppConfig:
    """Carga y retorna la configuración validada."""
    return AppConfig()
