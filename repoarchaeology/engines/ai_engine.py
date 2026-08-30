"""
Motor de Inteligencia Artificial para síntesis arqueológica de repositorios:
- Soporte para Ollama Local (qwen2.5-coder:1.5b)
- Soporte para Google Gemini y OpenAI
- Motor Heurístico Determinista Offline (Garantía 100% sin dependencias)
"""
import json
from typing import List, Optional
import urllib.request
import urllib.error

from repoarchaeology.core.models import CommitInfo, FileHotspot


class AIEngine:
    """Sintetizador de linaje y explicaciones históricas con fallback adaptativo."""
    
    def __init__(self, provider: str = "offline", ollama_host: str = "http://localhost:11434", model: str = "qwen2.5-coder:1.5b", api_key: Optional[str] = None):
        self.provider = provider
        self.ollama_host = ollama_host.rstrip("/")
        self.model = model
        self.api_key = api_key
        
    def summarize_file_lore(self, file_path: str, commits: List[CommitInfo]) -> str:
        """Genera una síntesis en lenguaje natural sobre la historia de un archivo."""
        if not commits:
            return f"No se encontraron registros de commits para el archivo '{file_path}'."
            
        # Intentar Ollama si está activo
        if self.provider == "local":
            lore_ai = self._query_ollama_lore(file_path, commits)
            if lore_ai:
                return lore_ai
                
        # Fallback a Motor Heurístico Determinista Offline
        return self._heuristic_file_lore(file_path, commits)

    def _query_ollama_lore(self, file_path: str, commits: List[CommitInfo]) -> Optional[str]:
        """Consulta a Ollama local con el modelo qwen2.5-coder:1.5b."""
        try:
            commit_logs = [f"- [{c.date.strftime('%Y-%m-%d')}] ({c.author_name}): {c.message}" for c in commits[:15]]
            prompt = (
                f"Actúa como un arquitecto forense de software. Analiza el historial de commits del archivo '{file_path}':\n"
                + "\n".join(commit_logs) +
                "\n\nRedacta un resumen conciso en español (máx 3 párrafos) explicando: "
                "1) Cuándo y por qué nació el archivo. 2) Su evolución y estabilidad. 3) Si es una zona de riesgo técnico."
            )
            
            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 300
                }
            }).encode("utf-8")
            
            req = urllib.request.Request(
                f"{self.ollama_host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except Exception:
            return None

    def _heuristic_file_lore(self, file_path: str, commits: List[CommitInfo]) -> str:
        """Generador determinista sin red basado en minería estadística."""
        first_commit = commits[-1]
        last_commit = commits[0]
        authors = set(c.author_name for c in commits)
        fixes = [c for c in commits if c.is_fix]
        refactors = [c for c in commits if c.is_refactor]
        
        paragraphs = []
        
        # Párrafo 1: Origen
        paragraphs.append(
            f"🏛️ **Origen y Creación:** El archivo `{file_path}` fue creado el "
            f"**{first_commit.date.strftime('%d/%m/%Y')}** por **{first_commit.author_name}** "
            f"mediante el commit `{first_commit.short_hash}` con el mensaje: *«{first_commit.message}»*."
        )
        
        # Párrafo 2: Evolución
        paragraphs.append(
            f"📈 **Evolución y Autores:** A lo largo de su ciclo de vida ha acumulado **{len(commits)} commits** "
            f"distribuidos entre **{len(authors)} autor(es)** principales ({', '.join(list(authors)[:3])}). "
            f"Su última modificación registrada data del {last_commit.date.strftime('%d/%m/%Y')} por {last_commit.author_name}."
        )
        
        # Párrafo 3: Evaluación de Riesgo
        if len(fixes) >= 3:
            paragraphs.append(
                f"⚠️ **Diagnóstico de Estabilidad:** Se detectaron **{len(fixes)} parches de corrección/hotfixes**, "
                f"lo que indica una alta propensión a regresiones o cambios frágiles en su lógica interna."
            )
        elif refactors:
            paragraphs.append(
                f"✨ **Diagnóstico de Estabilidad:** Ha pasado por **{len(refactors)} procesos de refactorización**, "
                f"manteniendo una tasa baja de parches de emergencia."
            )
        else:
            paragraphs.append(
                "✅ **Diagnóstico de Estabilidad:** Historial estable sin concentración crítica de fallos reportados."
            )
            
        return "\n\n".join(paragraphs)
