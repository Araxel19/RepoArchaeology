"""
Punto de entrada principal y despacho de comandos de RepoArchaeology.
"""
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from repoarchaeology import __version__
from repoarchaeology.core.config import load_config
from repoarchaeology.core.updater import perform_update, prompt_auto_update_if_needed
from repoarchaeology.engines.git_engine import GitEngine
from repoarchaeology.engines.ai_engine import AIEngine
from repoarchaeology.core.models import RepoHealthReport
from repoarchaeology.exporters.markdown_exporter import MarkdownExporter
from repoarchaeology.exporters.html_exporter import HTMLExporter
from repoarchaeology.exporters.json_exporter import JSONExporter

app = typer.Typer(
    name="repoarch",
    help="🏛️ RepoArchaeology - Arqueología forense de repositorios, linaje de decisiones y deuda técnica.",
    add_completion=False
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"[bold blue]RepoArchaeology[/bold blue] versión [bold green]{__version__}[/bold green]")
        raise typer.Exit()


@app.callback()
def main_callback(
    ctx: typer.Context,
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Muestra la versión de RepoArchaeology", callback=version_callback, is_eager=True
    ),
    no_update_check: bool = typer.Option(False, "--no-update-check", help="Desactiva la comprobación automática de actualizaciones")
):
    """Comprobación de actualizaciones en segundo plano antes de ejecutar comandos."""
    # No comprobar si es el propio comando de update o version
    if ctx.invoked_subcommand != "update" and not no_update_check:
        prompt_auto_update_if_needed()


@app.command(name="update")
def update_cmd():
    """
    🔄 Actualiza RepoArchaeology a la última versión disponible desde GitHub.
    """
    perform_update()


@app.command(name="doctor")
def doctor(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    commits_limit: int = typer.Option(200, "--commits", "-c", help="Límite de commits a analizar")
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
        
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Extrayendo historial y calculando métricas...", total=None)
            commits = engine.extract_commits(max_count=commits_limit)
            hotspots = engine.calculate_hotspots(commits)
            couplings = engine.detect_ghost_coupling(commits)
            bus_factors = engine.calculate_bus_factor(commits)
            
        if not commits:
            console.print("[yellow]No se encontraron commits suficientes en este repositorio.[/yellow]")
            return
            
        critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
        high_count = sum(1 for h in hotspots if h.risk_level == "HIGH")
        health_score = max(100 - (critical_count * 8) - (high_count * 3) - (len(couplings) * 2), 15)
        
        color = "green" if health_score >= 80 else ("yellow" if health_score >= 50 else "red")
        
        console.print(f"\n[bold]Puntaje de Salud Histórica:[/bold] [{color} bold]{health_score} / 100[/{color} bold]")
        console.print(f"Commits analizados: [cyan]{len(commits)}[/cyan] | Archivos auditados: [cyan]{len(hotspots)}[/cyan]\n")
        
        # Tabla resumen Hotspots
        table = Table(title="🔥 Archivos en Riesgo (Top Hotspots)", border_style="blue")
        table.add_column("Archivo", style="cyan")
        table.add_column("Commits", justify="right")
        table.add_column("Autores", justify="right")
        table.add_column("Hotfixes", justify="right")
        table.add_column("Autor Principal", style="magenta")
        table.add_column("Riesgo", justify="center")
        
        for h in hotspots[:5]:
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            table.add_row(
                h.file_path,
                str(h.commit_count),
                str(h.authors_count),
                str(h.fix_count),
                f"{h.top_author} ({h.top_author_percentage}%)",
                f"[{risk_color} bold]{h.risk_level}[/{risk_color} bold]"
            )
        console.print(table)
        
        # Resumen Bus Factor
        if bus_factors:
            top_b = bus_factors[0]
            if top_b.ownership_percentage >= 60.0:
                console.print(f"\n[bold red]⚠️ Alerta de Bus Factor:[/bold red] {top_b.author_name} concentra el [bold]{top_b.ownership_percentage}%[/bold] de los commits analizados.")
                
        if couplings:
            console.print(f"[bold yellow]👻 Se detectaron {len(couplings)} acoplamientos fantasma.[/bold yellow] Usa [cyan]repoarch coupling[/cyan] para verlos.\n")
            
    except Exception as e:
        console.print(f"[bold red]Error durante el diagnóstico:[/bold red] {e}")
        sys.exit(1)


@app.command(name="churn")
def churn(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio"),
    top: int = typer.Option(10, "--top", "-t", help="Número de archivos a listar"),
    commits_limit: int = typer.Option(300, "--commits", "-c", help="Límite de commits")
):
    """
    🔥 Detecta puntos calientes (hotspots) y alta rotación de código.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        hotspots = engine.calculate_hotspots(commits)
        
        table = Table(title=f"🔥 Top {top} Puntos Calientes (Code Churn)", border_style="blue")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Archivo", style="cyan")
        table.add_column("Commits", justify="right")
        table.add_column("Autores", justify="right")
        table.add_column("Hotfixes", justify="right")
        table.add_column("Churn Score", justify="right")
        table.add_column("Nivel de Riesgo", justify="center")
        
        for idx, h in enumerate(hotspots[:top], start=1):
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            table.add_row(
                str(idx),
                h.file_path,
                str(h.commit_count),
                str(h.authors_count),
                str(h.fix_count),
                f"{h.churn_score}%",
                f"[{risk_color} bold]{h.risk_level}[/{risk_color} bold]"
            )
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="coupling")
def coupling(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", "-m", help="Umbral mínimo de correlación (0.1 - 1.0)"),
    commits_limit: int = typer.Option(400, "--commits", "-c", help="Límite de commits")
):
    """
    👻 Descubre acoplamientos fantasma e invisibles entre módulos.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        couplings = engine.detect_ghost_coupling(commits, min_confidence=min_confidence)
        
        if not couplings:
            console.print("[green]No se detectaron acoplamientos fantasma por encima del umbral configurado.[/green]")
            return
            
        table = Table(title="👻 Acoplamientos Fantasma Detectados", border_style="yellow")
        table.add_column("Archivo A", style="cyan")
        table.add_column("Archivo B", style="magenta")
        table.add_column("Co-Commits", justify="right")
        table.add_column("Confianza", justify="right", style="bold green")
        table.add_column("Diagnóstico", style="dim")
        
        for c in couplings[:15]:
            table.add_row(
                c.file_a,
                c.file_b,
                str(c.co_commit_count),
                f"{int(c.confidence * 100)}%",
                c.explanation
            )
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="lore")
def lore(
    file_path: str = typer.Argument(..., help="Ruta relativa del archivo a auditar"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio"),
    commits_limit: int = typer.Option(300, "--commits", "-c", help="Límite de commits")
):
    """
    📜 Reconstruye la historia, contexto y linaje de decisiones de un archivo.
    """
    try:
        engine = GitEngine(path.resolve())
        all_commits = engine.extract_commits(max_count=commits_limit)
        file_commits = [c for c in all_commits if any(f.endswith(file_path) or f == file_path for f in c.files_changed)]
        
        config = load_config()
        ai = AIEngine(
            provider=config.ai_provider,
            ollama_host=config.ollama_host,
            model=config.ollama_model
        )
        summary = ai.summarize_file_lore(file_path, file_commits)
        
        console.print(Panel(
            summary,
            title=f"📜 Linaje Histórico: [bold cyan]{file_path}[/bold cyan]",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="breaking")
def breaking(
    base: str = typer.Option("main", "--base", "-b", help="Rama base estable"),
    target: str = typer.Option("develop", "--target", "-t", help="Rama objetivo con cambios"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio")
):
    """
    ⚡ Compara ramas y detecta eliminación de firmas públicas (Breaking Changes).
    """
    try:
        engine = GitEngine(path.resolve())
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description=f"Comparando {base}...{target} y analizando ASTs...", total=None)
            changes = engine.compare_branches_for_breaking_changes(base_branch=base, target_branch=target)
            
        if not changes:
            console.print(f"[green]✓ No se detectaron roturas de contrato o firmas eliminadas entre {base} y {target}.[/green]")
            return
            
        table = Table(title=f"⚡ Breaking Changes Detectados ({base} ↔ {target})", border_style="red")
        table.add_column("Archivo", style="cyan")
        table.add_column("Símbolo Afectado", style="bold red")
        table.add_column("Descripción", style="dim")
        
        for ch in changes:
            table.add_row(ch.file_path, ch.symbol_name, ch.description)
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="scan")
def scan(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio"),
    export: Optional[Path] = typer.Option(None, "--export", "-e", help="Ruta de exportación (formato deducido: .md, .html, .json)"),
    html: bool = typer.Option(False, "--html", help="Genera y abre automáticamente un reporte HTML")
):
    """
    📊 Ejecuta un escaneo forense completo y genera reportes técnicos en Markdown, HTML o JSON.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=400)
        hotspots = engine.calculate_hotspots(commits)
        couplings = engine.detect_ghost_coupling(commits)
        bus_factors = engine.calculate_bus_factor(commits)
        
        critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
        health_score = max(100 - (critical_count * 8) - (len(couplings) * 2), 15)
        
        recs = [
            f"Modularizar y añadir tests prioritarios a los {critical_count} archivos marcados como críticos.",
            "Desacoplar explícitamente los módulos que presentan co-modificación frecuente (acoplamiento fantasma).",
            "Distribuir el conocimiento en archivos mantenidos por un único autor para mejorar el bus factor."
        ]
        
        report = RepoHealthReport(
            repo_name=path.resolve().name,
            total_commits_analyzed=len(commits),
            total_files_analyzed=len(hotspots),
            health_score=health_score,
            bus_factor_score=int(100 - (bus_factors[0].ownership_percentage if bus_factors else 0)),
            hotspots=hotspots,
            ghost_couplings=couplings,
            top_authors=bus_factors[:5],
            recommendations=recs
        )
        
        if export:
            ext = export.suffix.lower()
            if ext == ".html":
                HTMLExporter.export(report, export.resolve())
            elif ext == ".json":
                JSONExporter.export(report, export.resolve())
            else:
                MarkdownExporter.export(report, export.resolve())
            console.print(f"[bold green]✓ Reporte exportado exitosamente a:[/bold green] {export.resolve()}")
        elif html:
            target_html = path.resolve() / "repoarch_report.html"
            HTMLExporter.export(report, target_html)
            console.print(f"[bold green]✓ Reporte interactivo HTML generado en:[/bold green] {target_html}")
        else:
            doctor(path=path)
    except Exception as e:
        console.print(f"[bold red]Error durante el escaneo:[/bold red] {e}")
        sys.exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
