"""
Punto de entrada principal de la CLI con Typer y Rich.
"""
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from repoarchaeology import __version__
from repoarchaeology.core.config import load_config
from repoarchaeology.engines.git_engine import GitEngine
from repoarchaeology.engines.ai_engine import AIEngine
from repoarchaeology.core.models import RepoHealthReport
from repoarchaeology.exporters.markdown_exporter import MarkdownExporter

app = typer.Typer(
    name="repoarch",
    help="🏛️ RepoArchaeology - Análisis forense de repositorios, linaje de decisiones y deuda técnica.",
    add_completion=False
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"[bold blue]RepoArchaeology[/bold blue] versión [bold green]{__version__}[/bold green]")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Muestra la versión de RepoArchaeology", callback=version_callback, is_eager=True
    )
):
    pass


@app.command(name="doctor")
def doctor(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git a evaluar"),
    commits_limit: int = typer.Option(100, "--commits", "-c", help="Cantidad de commits a inspeccionar")
):
    """
    🩺 Realiza un diagnóstico integral de salud histórica sobre el repositorio.
    """
    try:
        engine = GitEngine(path.resolve())
        console.print(Panel.fit(
            f"[bold blue]RepoArchaeology Doctor[/bold blue] · Analizando [cyan]{path.resolve().name}[/cyan]",
            border_style="blue"
        ))
        
        with console.status("[bold green]Extrayendo commits y calculando métricas forenses..."):
            commits = engine.extract_commits(max_count=commits_limit)
            hotspots = engine.calculate_hotspots(commits)
            couplings = engine.detect_ghost_coupling(commits)
            
        if not commits:
            console.print("[yellow]No se encontraron commits suficientes en este repositorio.[/yellow]")
            return
            
        # Calcular puntuación de salud simple
        critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
        health_score = max(100 - (critical_count * 8) - (len(couplings) * 3), 20)
        
        color = "green" if health_score >= 80 else ("yellow" if health_score >= 60 else "red")
        
        console.print(f"\n[bold]Puntaje de Salud Histórica:[/bold] [{color} bold]{health_score}/100[/{color} bold]")
        console.print(f"Commits analizados: [cyan]{len(commits)}[/cyan] | Archivos rastreados: [cyan]{len(hotspots)}[/cyan]\n")
        
        # Tabla resumen de Hotspots
        table = Table(title="🔥 Archivos de Mayor Riesgo (Top Hotspots)", border_style="dim")
        table.add_column("Archivo", style="cyan")
        table.add_column("Commits", justify="right")
        table.add_column("Autores", justify="right")
        table.add_column("Hotfixes", justify="right")
        table.add_column("Nivel de Riesgo", justify="center")
        
        for h in hotspots[:5]:
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            table.add_row(
                h.file_path,
                str(h.commit_count),
                str(h.authors_count),
                str(h.fix_count),
                f"[{risk_color}]{h.risk_level}[/{risk_color}]"
            )
        console.print(table)
        
        if couplings:
            console.print(f"\n[bold yellow]👻 Se detectaron {len(couplings)} acoplamientos fantasma significativos.[/bold yellow]")
            console.print("Usa [bold cyan]repoarch coupling[/bold cyan] para ver los detalles completos.\n")
            
    except Exception as e:
        console.print(f"[bold red]Error durante el diagnóstico:[/bold red] {e}")
        sys.exit(1)


@app.command(name="churn")
def churn(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    top: int = typer.Option(10, "--top", "-t", help="Número de archivos a mostrar"),
    commits_limit: int = typer.Option(300, "--commits", "-c", help="Límite de commits a analizar")
):
    """
    🔥 Detecta puntos calientes (hotspots) y alta rotación de código.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        hotspots = engine.calculate_hotspots(commits)
        
        table = Table(title=f"🔥 Top {top} Puntos Calientes (Code Churn)", border_style="blue")
        table.add_column("Pos", justify="right", style="dim")
        table.add_column("Archivo", style="cyan")
        table.add_column("Commits", justify="right")
        table.add_column("Autores", justify="right")
        table.add_column("Hotfixes", justify="right")
        table.add_column("Churn Score", justify="right")
        table.add_column("Riesgo", justify="center")
        
        for idx, h in enumerate(hotspots[:top], start=1):
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            table.add_row(
                str(idx),
                h.file_path,
                str(h.commit_count),
                str(h.authors_count),
                str(h.fix_count),
                f"{h.churn_score}%",
                f"[{risk_color}]{h.risk_level}[/{risk_color}]"
            )
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="coupling")
def coupling(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", "-m", help="Umbral de correlación (0.1 a 1.0)"),
    commits_limit: int = typer.Option(400, "--commits", "-c", help="Límite de commits")
):
    """
    👻 Descubre acoplamientos fantasma entre archivos del repositorio.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        couplings = engine.detect_ghost_coupling(commits, min_confidence=min_confidence)
        
        if not couplings:
            console.print("[green]No se detectaron acoplamientos fantasma por encima del umbral.[/green]")
            return
            
        table = Table(title="👻 Acoplamientos Fantasma Detectados", border_style="yellow")
        table.add_column("Archivo A", style="cyan")
        table.add_column("Archivo B", style="magenta")
        table.add_column("Co-Commits", justify="right")
        table.add_column("Confianza", justify="right", style="bold green")
        
        for c in couplings[:15]:
            table.add_row(
                c.file_a,
                c.file_b,
                str(c.co_commit_count),
                f"{int(c.confidence * 100)}%"
            )
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="lore")
def lore(
    file_path: str = typer.Argument(..., help="Ruta relativa del archivo a investigar"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    commits_limit: int = typer.Option(200, "--commits", "-c", help="Límite de commits a analizar")
):
    """
    📜 Reconstruye la historia, contexto y linaje de decisiones de un archivo.
    """
    try:
        engine = GitEngine(path.resolve())
        all_commits = engine.extract_commits(max_count=commits_limit)
        file_commits = [c for c in all_commits if any(f.endswith(file_path) for f in c.files_changed)]
        
        ai = AIEngine(provider="offline")
        summary = ai.summarize_file_lore(file_path, file_commits)
        
        console.print(Panel(
            summary,
            title=f"📜 Linaje Histórico: {file_path}",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="scan")
def scan(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    export: Optional[Path] = typer.Option(None, "--export", "-e", help="Ruta para exportar el reporte en Markdown")
):
    """
    📊 Ejecuta un escaneo completo y opcionalmente exporta el reporte técnico.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=300)
        hotspots = engine.calculate_hotspots(commits)
        couplings = engine.detect_ghost_coupling(commits)
        
        critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
        health_score = max(100 - (critical_count * 8) - (len(couplings) * 3), 20)
        
        recs = [
            f"Revisar modularización en los {critical_count} archivos marcados como críticos.",
            "Desacoplar explícitamente los módulos que presentan co-modificación frecuente.",
            "Distribuir el conocimiento en archivos mantenidos por un único autor histórico."
        ]
        
        report = RepoHealthReport(
            repo_name=path.resolve().name,
            total_commits_analyzed=len(commits),
            total_files_analyzed=len(hotspots),
            health_score=health_score,
            hotspots=hotspots,
            ghost_couplings=couplings,
            recommendations=recs
        )
        
        if export:
            MarkdownExporter.export(report, export.resolve())
            console.print(f"[bold green]✓ Reporte exportado exitosamente a:[/bold green] {export.resolve()}")
        else:
            doctor(path=path)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
