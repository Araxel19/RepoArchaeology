"""
Generador de reportes visuales en HTML interactivo con Dark Mode moderno.
"""
from pathlib import Path
from repoarchaeology.core.models import RepoHealthReport


class HTMLExporter:
    """Exportador a Dashboard HTML autónomo y estético."""
    
    @staticmethod
    def export(report: RepoHealthReport, output_path: Path) -> None:
        hotspots_rows = []
        for h in report.hotspots[:20]:
            badge_color = "#ef4444" if h.risk_level == "CRITICAL" else ("#f59e0b" if h.risk_level == "HIGH" else "#10b981")
            hotspots_rows.append(f"""
            <tr>
                <td style="font-family: monospace; color: #38bdf8;">{h.file_path}</td>
                <td>{h.commit_count}</td>
                <td>{h.authors_count}</td>
                <td>{h.fix_count}</td>
                <td><span style="background: {badge_color}22; color: {badge_color}; padding: 4px 8px; border-radius: 4px; font-weight: bold; border: 1px solid {badge_color};">{h.risk_level}</span></td>
                <td>{h.churn_score}%</td>
            </tr>
            """)
            
        couplings_rows = []
        for g in report.ghost_couplings[:15]:
            couplings_rows.append(f"""
            <tr>
                <td style="font-family: monospace; color: #38bdf8;">{g.file_a}</td>
                <td style="font-family: monospace; color: #c084fc;">{g.file_b}</td>
                <td>{g.co_commit_count}</td>
                <td><b>{int(g.confidence * 100)}%</b></td>
                <td style="color: #94a3b8; font-size: 0.9em;">{g.explanation}</td>
            </tr>
            """)

        recs_list = "".join(f"<li>{r}</li>" for r in report.recommendations)

        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RepoArchaeology Report · {report.repo_name}</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --muted: #94a3b8;
            --primary: #3b82f6;
            --border: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 30px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border-bottom: 2px solid var(--primary);
            padding: 24px;
            border-radius: 12px;
            margin-bottom: 24px;
        }}
        h1 {{ margin: 0 0 8px 0; color: #fff; }}
        .meta {{ color: var(--muted); font-size: 0.9em; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 8px; padding: 20px; }}
        .score {{ font-size: 2.8em; font-weight: bold; color: #10b981; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid var(--border); }}
        th {{ background: #0f172a; color: var(--muted); font-weight: 600; }}
        tr:hover {{ background: #1e293b88; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🏛️ RepoArchaeology Report: {report.repo_name}</h1>
            <div class="meta">Generado el {report.scan_date.strftime('%Y-%m-%d %H:%M:%S UTC')} · Diagnóstico Forense de Software</div>
        </header>

        <div class="grid">
            <div class="card">
                <div style="color: var(--muted);">Puntaje de Salud Histórica</div>
                <div class="score">{report.health_score} <span style="font-size: 0.4em; color: var(--muted);">/ 100</span></div>
            </div>
            <div class="card">
                <div style="color: var(--muted);">Commits Analizados</div>
                <div class="score" style="color: #38bdf8;">{report.total_commits_analyzed}</div>
            </div>
            <div class="card">
                <div style="color: var(--muted);">Archivos Auditados</div>
                <div class="score" style="color: #c084fc;">{report.total_files_analyzed}</div>
            </div>
        </div>

        <div class="card" style="margin-bottom: 24px;">
            <h2 style="margin-top: 0; color: #38bdf8;">🩺 Recomendaciones Clave</h2>
            <ul>{recs_list}</ul>
        </div>

        <div class="card" style="margin-bottom: 24px;">
            <h2 style="margin-top: 0; color: #f59e0b;">🔥 Puntos Calientes (Top Hotspots)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Archivo</th>
                        <th>Commits</th>
                        <th>Autores</th>
                        <th>Hotfixes</th>
                        <th>Nivel de Riesgo</th>
                        <th>Churn Score</th>
                    </tr>
                </thead>
                <tbody>{''.join(hotspots_rows)}</tbody>
            </table>
        </div>

        <div class="card">
            <h2 style="margin-top: 0; color: #a855f7;">👻 Acoplamientos Fantasma Detectados</h2>
            <table>
                <thead>
                    <tr>
                        <th>Archivo A</th>
                        <th>Archivo B</th>
                        <th>Co-Commits</th>
                        <th>Confianza</th>
                        <th>Detalle</th>
                    </tr>
                </thead>
                <tbody>{''.join(couplings_rows)}</tbody>
            </table>
        </div>
    </div>
</body>
</html>
"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
