"""
Exportador a formato estructurado JSON para pipelines CI/CD.
"""
from pathlib import Path
from repoarchaeology.core.models import RepoHealthReport


class JSONExporter:
    """Exportador de métricas en JSON serializado."""
    
    @staticmethod
    def export(report: RepoHealthReport, output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
