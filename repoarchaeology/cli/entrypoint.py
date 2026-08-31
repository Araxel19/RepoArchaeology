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
from rich.columns import Columns
from rich.text import Text

from repoarchaeology import __version__
from repoarchaeology.core.config import load_config
from repoarchaeology.core.updater import perform_update, prompt_auto_update_if_needed
from repoarchaeology.engines.git_engine import (
    GitEngine, get_file_role, generate_coupling_insight,
    is_auto_generated, is_infra_only, is_high_level_config
)
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
    if ctx.invoked_subcommand != "update" and not no_update_check:
        prompt_auto_update_if_needed()


@app.command(name="update")
def update_cmd():
    """
    🔄 Actualiza RepoArchaeology a la última versión disponible desde GitHub.
    """
    perform_update()


def _generate_hotspot_action(file_path: str, fix_count: int, authors_count: int, top_author_pct: float) -> str:
    """
    Genera una recomendación concreta, contextual al tipo de archivo y sus métricas.
    Evita sugerir acciones que no aplican (ej: tests a un archivo YAML de configuración).
    """
    fp = file_path.lower()
    name = Path(file_path).name
    ext = Path(file_path).suffix.lower()

    # ── Archivos de localización / traducción (.arb, .po, .strings) ────────────
    if ext in (".arb",) or "l10n" in fp or "locali" in fp or "i18n" in fp or "intl" in fp:
        if fix_count >= 3:
            return f"Traducciones con {fix_count} correcciones. Automatiza la validación de claves ausentes en CI para evitar que falten textos en algún idioma."
        if authors_count >= 3:
            return "Múltiples autores editando traducciones. Define un flujo claro: un PR por idioma o uso de Crowdin/Lokalise para centralizar el proceso."
        return "Recurso de localización con alta rotación. Considera un script que verifique que todos los idiomas tengan las mismas claves antes de hacer merge."

    # ── Archivos de configuración de proyecto (pubspec.yaml, package.json…) ────
    if is_high_level_config(file_path):
        if fix_count >= 5:
            return f"Dependencias corregidas {fix_count} veces. Ejecuta `dependency audit` periódicamente y fija versiones exactas para evitar roturas silenciosas."
        if authors_count >= 3:
            return "Múltiples personas tocando las dependencias. Designa un responsable de dependencias y usa un bot (Dependabot/Renovate) para actualizaciones automáticas."
        return "Alta rotación en las dependencias. Considera usar rangos semánticos controlados y documentar el motivo de cada cambio de versión en el CHANGELOG."

    # ── Archivos de autenticación / seguridad ───────────────────────────────────
    if any(w in fp for w in ["auth", "login", "session", "token", "credential", "secret", "jwt", "oauth", "permission", "role"]):
        if fix_count >= 3:
            return f"Componente de autenticación con {fix_count} correcciones. Cada cambio aquí es un riesgo de seguridad. Agrega revisión obligatoria de seguridad (security review) antes de mergear."
        if top_author_pct >= 85:
            return "Autenticación casi exclusiva de un autor. Documenta el flujo completo y haz al menos una revisión cruzada por sprint para no depender de una sola persona en lo más crítico."
        return "Lógica de autenticación con alta rotación. Asegúrate de tener tests de integración que cubran los flujos de login, logout y renovación de sesión."

    # ── Pantallas / páginas de UI (screen, page, view) ─────────────────────────
    if any(w in fp for w in ["screen", "page", "view", "_ui", "widget", "component", "dialog", "modal", "sheet"]):
        if fix_count >= 5:
            return f"Pantalla con {fix_count} correcciones. Probablemente tiene demasiada lógica mezclada con la UI. Extrae la lógica de negocio a un ViewModel o Bloc y agrega widget tests."
        if authors_count >= 4:
            return f"Pantalla modificada por {authors_count} autores sin coordinación. Define si el componente pertenece a una feature específica y asigna un responsable."
        if top_author_pct >= 90:
            return "UI crítica con un único autor. Programa una revisión de diseño y asegúrate de que hay al menos un widget test para los flujos principales."
        return "Alta rotación en la UI. Considera dividir el archivo en widgets más pequeños y reutilizables para facilitar el mantenimiento."

    # ── Rutas / controladores de API ────────────────────────────────────────────
    if any(w in fp for w in ["route", "router", "controller", "handler", "endpoint", "api"]):
        if fix_count >= 4:
            return f"Ruta o controlador con {fix_count} correcciones. Define contratos claros (OpenAPI/Swagger) para cada endpoint y agrega tests de integración de API."
        if authors_count >= 3:
            return f"Múltiples autores en el controlador. Establece una convención de respuestas API y valida que todos los endpoints usen el mismo formato de error."
        return "Alta rotación en rutas. Asegúrate de documentar los parámetros, respuestas y casos de error de cada endpoint."

    # ── Servicios / lógica de negocio ───────────────────────────────────────────
    if any(w in fp for w in ["service", "usecase", "use_case", "interactor", "domain", "repository", "repo"]):
        if fix_count >= 4:
            return f"Servicio con {fix_count} correcciones en el historial. Agrega tests unitarios que cubran los casos de error específicos que generaron esos fixes."
        if top_author_pct >= 90:
            return "Servicio dominado por un autor. Documenta los contratos de entrada/salida y transfiere conocimiento con una sesión de pair programming."
        return "Lógica de negocio con alta rotación. Verifica que las responsabilidades están bien delimitadas y que no hay lógica de presentación mezclada."

    # ── Esquemas de base de datos / migraciones ──────────────────────────────────
    if any(w in fp for w in ["migration", "schema", "seed", "database", "db", ".sql"]):
        if fix_count >= 3:
            return f"Esquema de base de datos con {fix_count} correcciones. Revisa que todas las migraciones sean reversibles (down migrations) y estén probadas en un entorno de staging."
        return "Base de datos con alta rotación. Documenta cada migración con el motivo del cambio y verifica que no hay datos perdidos en el proceso."

    # ── Tests ────────────────────────────────────────────────────────────────────
    if any(w in fp for w in ["_test.", "test_", "/test/", "/tests/", "spec.", "_spec."]):
        return "El propio archivo de tests cambia frecuentemente. Verifica que los tests son estables y no están acoplados a detalles de implementación que cambian seguido."

    # ── Archivos de scripts / CI / configuración de entorno ─────────────────────
    if ext in (".sh", ".bash", ".ps1", ".bat") or any(w in fp for w in ["dockerfile", "docker-compose", "ci", "pipeline", "workflow"]):
        return "Script de infraestructura con alta rotación. Considera parametrizar las variables de entorno y agregar al menos una prueba de smoke test en el pipeline."

    # ── Fallback genérico pero con variación por métricas ───────────────────────
    if fix_count >= 5:
        return f"Alta tasa de correcciones ({fix_count} fixes en el historial). Analiza qué tipo de errores se repiten y si hay un patrón que pueda prevenirse con mejores abstracciones."
    if top_author_pct >= 90:
        return f"Archivo casi exclusivo de un autor ({top_author_pct}%). Incluye a otro desarrollador en las revisiones de PR para distribuir el conocimiento gradualmente."
    if authors_count >= 4:
        return f"Demasiados autores ({authors_count}) sin un propietario claro. Define quién tiene la última palabra en los cambios a este archivo para evitar inconsistencias."
    return f"Alta rotación de código. Evalúa si {name} tiene demasiadas responsabilidades y podría dividirse en partes más pequeñas."


@app.command(name="doctor")
def doctor(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    commits_limit: int = typer.Option(200, "--commits", "-c", help="Límite de commits a analizar"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados en el análisis"),
    include_infra: bool = typer.Option(False, "--include-infra", help="Incluir archivos de infraestructura/docs en el análisis"),
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
            hotspots = engine.calculate_hotspots(
                commits,
                exclude_generated=not include_generated,
                exclude_infra=not include_infra,
            )
            couplings = engine.detect_ghost_coupling(
                commits,
                exclude_generated=not include_generated,
                exclude_infra=not include_infra,
            )
            bus_factors = engine.calculate_bus_factor(commits)

        if not commits:
            console.print("[yellow]No se encontraron commits suficientes en este repositorio.[/yellow]")
            return

        critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
        high_count = sum(1 for h in hotspots if h.risk_level == "HIGH")
        health_score = max(100 - (critical_count * 8) - (high_count * 3) - (len(couplings) * 1), 15)

        color = "green" if health_score >= 80 else ("yellow" if health_score >= 50 else "red")

        console.print(f"\n[bold]Puntaje de Salud Histórica:[/bold] [{color} bold]{health_score} / 100[/{color} bold]")
        console.print(f"Commits analizados: [cyan]{len(commits)}[/cyan] | Archivos de código analizados: [cyan]{len(hotspots)}[/cyan]\n")


        # ── Tabla compacta de métricas (sin columna "Qué hacer" para que no se corte) ──

        table = Table(title="🔥 Archivos de Código en Mayor Riesgo", border_style="blue", show_lines=True)
        table.add_column("#", style="dim", justify="right", width=3)
        table.add_column("Archivo", style="cyan", ratio=4)
        table.add_column("Tipo", style="dim", ratio=3)
        table.add_column("Commits", justify="right", width=8)
        table.add_column("Fixes", justify="right", width=6)
        table.add_column("Autores", justify="right", width=8)
        table.add_column("Propietario", style="magenta", ratio=3)
        table.add_column("Riesgo", justify="center", width=10)

        top_hotspots = hotspots[:5]
        for idx, h in enumerate(top_hotspots, start=1):
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            table.add_row(
                str(idx),
                h.file_path,
                get_file_role(h.file_path),
                str(h.commit_count),
                str(h.fix_count),
                str(h.authors_count),
                f"{h.top_author} ({h.top_author_percentage}%)",
                f"[{risk_color} bold]{h.risk_level}[/{risk_color} bold]",
            )
        console.print(table)

        # ── Recomendaciones como lista numerada en panel separado ──
        if top_hotspots:
            rec_lines = []
            for idx, h in enumerate(top_hotspots, start=1):
                action = _generate_hotspot_action(h.file_path, h.fix_count, h.authors_count, h.top_author_percentage)
                name = Path(h.file_path).name
                rec_lines.append(f"  [bold cyan]{idx}. {name}[/bold cyan] — {action}")
            console.print(Panel(
                "\n".join(rec_lines),
                title="💡 Recomendaciones por Archivo",
                border_style="cyan",
                padding=(0, 1),
            ))

        # Bus factor
        if bus_factors:
            top_b = bus_factors[0]
            if top_b.ownership_percentage >= 70.0:
                console.print(
                    f"\n[bold red]⚠️  Riesgo de Bus Factor:[/bold red] "
                    f"[bold]{top_b.author_name}[/bold] concentra el [bold]{top_b.ownership_percentage}%[/bold] "
                    f"de los commits y es propietario de [bold]{top_b.files_owned_count}[/bold] archivo(s). "
                    f"Si sale del proyecto, el conocimiento se pierde. "
                    f"[dim]→ Programa pair programming o revisiones cruzadas.[/dim]"
                )
            elif top_b.ownership_percentage >= 50.0:
                console.print(
                    f"\n[bold yellow]⚡ Bus Factor Moderado:[/bold yellow] "
                    f"[bold]{top_b.author_name}[/bold] lidera con {top_b.ownership_percentage}% de participación. "
                    f"[dim]→ Distribuye gradualmente el conocimiento.[/dim]"
                )

        # Acoplamientos
        if couplings:
            high_conf = sum(1 for c in couplings if c.confidence >= 0.8)
            console.print(
                f"\n[bold yellow]👻 {len(couplings)} acoplamiento(s) invisible(s) detectado(s)[/bold yellow] "
                f"([bold red]{high_conf} con confianza ≥80%[/bold red]). "
                f"Usa [cyan]repoarch coupling[/cyan] para ver diagnósticos y qué refactorizar.\n"
            )
        else:
            console.print("\n[green]✓ No se detectaron acoplamientos fantasma significativos.[/green]\n")

        if not include_generated:
            console.print("[dim]ℹ️  Archivos auto-generados e infraestructura excluidos. Usa --include-generated o --include-infra para incluirlos.[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error durante el diagnóstico:[/bold red] {e}")
        sys.exit(1)



@app.command(name="churn")
def churn(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio"),
    top: int = typer.Option(10, "--top", "-t", help="Número de archivos a listar"),
    commits_limit: int = typer.Option(300, "--commits", "-c", help="Límite de commits"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados"),
    include_infra: bool = typer.Option(False, "--include-infra", help="Incluir archivos de infraestructura"),
):
    """
    🔥 Detecta puntos calientes (hotspots) y alta rotación de código.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        hotspots = engine.calculate_hotspots(
            commits,
            exclude_generated=not include_generated,
            exclude_infra=not include_infra,
        )

        table = Table(title=f"🔥 Top {top} Puntos Calientes de Código (Code Churn)", border_style="blue", show_lines=True)
        table.add_column("#", justify="right", style="dim")
        table.add_column("Archivo", style="cyan")
        table.add_column("Tipo", style="dim")
        table.add_column("Commits", justify="right")
        table.add_column("Fixes", justify="right")
        table.add_column("Autores", justify="right")
        table.add_column("Churn", justify="right")
        table.add_column("Riesgo", justify="center")
        table.add_column("Acción Recomendada", style="dim")

        for idx, h in enumerate(hotspots[:top], start=1):
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            action = _generate_hotspot_action(h.file_path, h.fix_count, h.authors_count, h.top_author_percentage)
            table.add_row(
                str(idx),
                h.file_path,
                get_file_role(h.file_path),
                str(h.commit_count),
                str(h.fix_count),
                str(h.authors_count),
                f"{h.churn_score}%",
                f"[{risk_color} bold]{h.risk_level}[/{risk_color} bold]",
                action,
            )
        console.print(table)
        if not include_generated:
            console.print("[dim]ℹ️  Archivos auto-generados y de infraestructura excluidos. Usa --include-generated para incluirlos.[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="coupling")
def coupling(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", "-m", help="Umbral mínimo de correlación (0.1 - 1.0)"),
    commits_limit: int = typer.Option(400, "--commits", "-c", help="Límite de commits"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados"),
    include_infra: bool = typer.Option(False, "--include-infra", help="Incluir archivos de infraestructura"),
):
    """
    👻 Descubre acoplamientos fantasma e invisibles entre módulos.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        couplings = engine.detect_ghost_coupling(
            commits,
            min_confidence=min_confidence,
            exclude_generated=not include_generated,
            exclude_infra=not include_infra,
        )

        if not couplings:
            console.print("[green]✓ No se detectaron acoplamientos fantasma por encima del umbral configurado.[/green]")
            return

        table = Table(title="👻 Acoplamientos Fantasma en Código Fuente", border_style="yellow", show_lines=True)
        table.add_column("Archivo A", style="cyan")
        table.add_column("Archivo B", style="magenta")
        table.add_column("Co-Commits", justify="right")
        table.add_column("Confianza", justify="right", style="bold")
        table.add_column("Diagnóstico y Acción", style="dim")

        for c in couplings[:15]:
            conf_color = "bold red" if c.confidence >= 0.8 else ("bold yellow" if c.confidence >= 0.6 else "bold green")
            table.add_row(
                c.file_a,
                c.file_b,
                str(c.co_commit_count),
                f"[{conf_color}]{int(c.confidence * 100)}%[/{conf_color}]",
                c.explanation,
            )
        console.print(table)

        high_conf = [c for c in couplings if c.confidence >= 0.8]
        if high_conf:
            console.print(f"\n[bold red]🔴 {len(high_conf)} par(es) con confianza crítica (≥80%):[/bold red] estas dependencias no documentadas son las que más riesgo representan para refactorizaciones futuras.")
        if not include_generated:
            console.print("\n[dim]ℹ️  Archivos auto-generados excluidos del análisis para reducir falsos positivos.[/dim]")
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
    export: Optional[Path] = typer.Option(None, "--export", "-e", help="Ruta de exportación (.md, .html, .json)"),
    html: bool = typer.Option(False, "--html", help="Genera un reporte HTML interactivo"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados"),
):
    """
    📊 Ejecuta un escaneo forense completo y genera reportes en Markdown, HTML o JSON.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=400)
        hotspots = engine.calculate_hotspots(commits, exclude_generated=not include_generated)
        couplings = engine.detect_ghost_coupling(commits, exclude_generated=not include_generated)
        bus_factors = engine.calculate_bus_factor(commits)

        critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
        high_count = sum(1 for h in hotspots if h.risk_level == "HIGH")
        health_score = max(100 - (critical_count * 8) - (high_count * 3) - (len(couplings)), 15)

        recs = [
            f"Añadir tests unitarios y de integración prioritariamente a los {critical_count} archivos críticos.",
            "Revisar los acoplamientos de alta confianza y evaluar si requieren una interfaz intermedia.",
            "Programar sesiones de pair programming para distribuir el conocimiento entre autores.",
            "Documentar las dependencias implícitas encontradas en los acoplamientos fantasma.",
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
            console.print(f"[bold green]✓ Reporte exportado a:[/bold green] {export.resolve()}")
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
