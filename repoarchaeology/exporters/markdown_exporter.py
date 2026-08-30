"""
Exportador de diagnósticos en formato Markdown profesional.
"""
from pathlib import Path
from repoarchaeology.core.models import RepoHealthReport


class MarkdownExporter:
    """Genera reportes técnicos en Markdown."""
    
    @staticmethod
    def export(report: RepoHealthReport, output_path: Path) -> None:
        content = [
            f"# 🏛️ Reporte Forense de Repositorio: {report.repo_name}",
            f"*Generado el {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            "",
            "---",
            "",
            "## 🩺 Diagnóstico General de Salud",
            f"- **Puntaje de Salud Histórica:** `{report.health_score} / 100`",
            f"- **Total de Commits Analizados:** `{report.total_commits_analyzed}`",
            f"- **Archivos Auditados:** `{report.total_files_analyzed}`",
            "",
            "### Recomendaciones Clave",
        ]
        
        for rec in report.recommendations:
            content.append(f"- {rec}")
            
        content.extend([
            "",
            "---",
            "",
            "## 🔥 Puntos Calientes y Código Frágil (Top Hotspots)",
            "| Archivo | Commits | Autores | Hotfixes | Nivel de Riesgo | Churn Score |",
            "| :--- | :---: | :---: | :---: | :---: | :---: |"
        ])
        
        for h in report.hotspots[:15]:
            content.append(
                f"| `{h.file_path}` | {h.commit_count} | {h.authors_count} | {h.fix_count} | **{h.risk_level}** | {h.churn_score}% |"
            )
            
        content.extend([
            "",
            "---",
            "",
            "## 👻 Acoplamiento Fantasma Detectado",
            "| Archivo A | Archivo B | Co-Commits | Confianza |",
            "| :--- | :--- | :---: | :---: |"
        ])
        
        for g in report.ghost_couplings[:10]:
            content.append(
                f"| `{g.file_a}` | `{g.file_b}` | {g.co_commit_count} | {int(g.confidence * 100)}% |"
            )
            
        content.append("\n*Reporte generado por RepoArchaeology (MIT License)*\n")
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(content), encoding="utf-8")
