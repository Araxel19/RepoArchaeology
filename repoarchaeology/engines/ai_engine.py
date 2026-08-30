"""
Motor de inferencia y síntesis histórica con soporte offline y conectores opcionales.
"""
from typing import List, Optional
from repoarchaeology.core.models import CommitInfo, FileHotspot


class AIEngine:
    """Motor de síntesis de linaje histórico."""
    
    def __init__(self, provider: str = "offline", api_key: Optional[str] = None):
        self.provider = provider
        self.api_key = api_key
        
    def summarize_file_lore(self, file_path: str, commits: List[CommitInfo]) -> str:
        """Genera una síntesis en lenguaje natural sobre la historia de un archivo."""
        if not commits:
            return f"No se encontraron registros históricos suficientes para '{file_path}'."
            
        authors = set(c.author_name for c in commits)
        fixes = [c for c in commits if c.is_fix]
        first_commit = commits[-1]
        last_commit = commits[0]
        
        summary = (
            f"El archivo '{file_path}' fue introducido el {first_commit.date.strftime('%Y-%m-%d')} "
            f"por {first_commit.author_name} con el mensaje: '{first_commit.message}'.\n\n"
            f"A lo largo de su historia, ha acumulado {len(commits)} modificaciones realizadas por "
            f"{len(authors)} autor(es) ({', '.join(list(authors)[:3])}). "
        )
        
        if fixes:
            summary += (
                f"Presenta una tasa de corrección activa con {len(fixes)} parches de errores/hotfixes "
                f"registrados, lo que sugiere que es un componente sensible a regresiones."
            )
        else:
            summary += "No registra un historial crítico de hotfixes recurrentes."
            
        return summary
