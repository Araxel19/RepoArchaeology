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
from repoarchaeology.engines.git_engine import (
    GitEngine, get_file_role, generate_coupling_insight,
    is_auto_generated, is_infra_only, is_high_level_config, is_l10n
)
from repoarchaeology.engines.ai_engine import AIEngine
from repoarchaeology.core.models import RepoHealthReport
from repoarchaeology.exporters.markdown_exporter import MarkdownExporter
from repoarchaeology.exporters.html_exporter import HTMLExporter
from repoarchaeology.exporters.json_exporter import JSONExporter

app = typer.Typer(
    name="repoarch",
    help="🏛️ [bold blue]RepoArchaeology[/bold blue] — Plataforma forense de repositorios Git, linaje de decisiones, acoplamiento invisible y deuda técnica.",
    add_completion=False,
    rich_markup_mode="rich"
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
        None, "--version", "-v", help="Muestra la versión instalada de RepoArchaeology", callback=version_callback, is_eager=True
    ),
    no_update_check: bool = typer.Option(False, "--no-update-check", help="Desactiva la comprobación automática de actualizaciones al iniciar")
):
    """Comprobación de actualizaciones en segundo plano antes de ejecutar comandos."""
    if ctx.invoked_subcommand != "update" and not no_update_check:
        prompt_auto_update_if_needed()


@app.command(name="update")
def update_cmd():
    """
    🔄 [bold]Actualiza RepoArchaeology[/bold] a la última versión disponible desde GitHub.
    Descarga cambios de forma segura (fast-forward), actualiza dependencias y valida la instalación.
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
    if is_l10n(file_path):
        if fix_count >= 3:
            return f"Traducciones con {fix_count} correcciones. Automatiza la validación de claves ausentes en CI para evitar que falten textos en algún idioma."
        if authors_count >= 3:
            return "Múltiples autores editando traducciones. Define un flujo centralizado (Crowdin/Lokalise o PR por idioma)."
        return "Recurso de localización con rotación activa. Verifica periódicamente que todos los idiomas tengan paridad de claves."

    # ── Archivos de configuración de proyecto (pubspec.yaml, package.json…) ────
    if is_high_level_config(file_path):
        if fix_count >= 5:
            return f"Dependencias modificadas/corregidas {fix_count} veces. Ejecuta auditorías periódicas de vulnerabilidades y fija versiones estables."
        if authors_count >= 3:
            return "Múltiples personas gestionando dependencias. Centraliza las actualizaciones con un bot (Dependabot/Renovate)."
        return "Alta actividad en dependencias. Mantén un registro claro de cambios en el CHANGELOG al actualizar versiones mayores."

    # ── Archivos de autenticación / seguridad ───────────────────────────────────
    if any(w in fp for w in ["auth", "login", "session", "token", "credential", "secret", "jwt", "oauth", "permission", "role"]):
        if fix_count >= 3:
            return f"Autenticación con {fix_count} correcciones históricas. Requiere revisión estricta de seguridad antes de cualquier merge."
        if top_author_pct >= 85:
            return "Lógica de autenticación concentrada en un único autor. Documenta el flujo de sesión y programa revisiones cruzadas."
        return "Módulo de autenticación crítico. Asegura tests de integración para login, renovación de token y revocación de sesión."

    # ── Pantallas / páginas de UI (screen, page, view, component) ───────────────
    if any(w in fp for w in ["screen", "page", "view", "_ui", "widget", "component", "dialog", "modal", "sheet"]):
        is_web_or_react = ext in (".jsx", ".tsx", ".vue", ".svelte", ".js", ".ts")
        if fix_count >= 5:
            if is_web_or_react:
                return f"Componente con {fix_count} correcciones. Extrae la lógica a Custom Hooks o Servicios y añade tests de componentes."
            return f"Pantalla con {fix_count} correcciones. Probable exceso de lógica en UI. Extrae la lógica a un ViewModel o Bloc y añade widget tests."
        if authors_count >= 4:
            return f"Componente editado por {authors_count} autores. Define un responsable de la feature para mantener la consistencia visual."
        if top_author_pct >= 90:
            return "UI desarrollada casi en su totalidad por un autor. Añade tests de regresión visual o pruebas de interacción para los flujos clave."
        return "Alta rotación de UI. Divide en subcomponentes más pequeños y reutilizables para simplificar el mantenimiento."

    # ── Rutas / controladores de API ────────────────────────────────────────────
    if any(w in fp for w in ["route", "router", "controller", "handler", "endpoint", "api"]):
        if fix_count >= 4:
            return f"Rutas/controlador con {fix_count} correcciones. Define contratos estrictos (OpenAPI/Swagger) y añade tests de integración de API."
        if authors_count >= 3:
            return "Múltiples autores en el controlador. Estandariza el formato de respuestas y el manejo de errores global."
        return "Alta rotación en rutas. Documenta parámetros, respuestas y códigos de estado esperados."

    # ── Servicios / lógica de negocio / repositorios ────────────────────────────
    if any(w in fp for w in ["service", "usecase", "use_case", "interactor", "domain", "repository", "repo"]):
        if fix_count >= 4:
            return f"Servicio con {fix_count} correcciones. Añade tests unitarios focalizados en los casos borde que causaron esos bugs."
        if top_author_pct >= 90:
            return "Lógica de negocio dominada por un autor. Documenta los contratos de entrada/salida y transfiere conocimiento con pair programming."
        return "Lógica de negocio con alta rotación. Asegura que las responsabilidades estén bien delimitadas sin acoplamiento a la UI."

    # ── Esquemas de base de datos / migraciones ──────────────────────────────────
    if any(w in fp for w in ["migration", "schema", "seed", "database", "db", ".sql"]):
        if fix_count >= 3:
            return f"Esquema de datos con {fix_count} correcciones. Verifica que todas las migraciones sean reversibles y probadas en staging."
        return "Base de datos con alta rotación. Documenta cada migración con el motivo del cambio y valida la integridad referencial."

    # ── Tests ────────────────────────────────────────────────────────────────────
    if any(w in fp for w in ["_test.", "test_", "/test/", "/tests/", "spec.", "_spec."]):
        return "Archivo de tests modificado frecuentemente. Verifica que los tests no dependan de detalles de implementación frágiles."

    # ── Fallback ─────────────────────────────────────────────────────────────────
    if fix_count >= 5:
        return f"Alta tasa de correcciones ({fix_count} fixes). Analiza el historial de errores para detectar patrones comunes y aplicar abstracciones."
    if top_author_pct >= 90:
        return f"Archivo casi exclusivo de un autor ({top_author_pct}%). Incluye a otro colaborador en las revisiones de código para compartir conocimiento."
    if authors_count >= 4:
        return f"Múltiples autores ({authors_count}) sin propietario claro. Asigna responsabilidad sobre este módulo para evitar inconsistencias."
    return f"Alta rotación de código. Evalúa si {name} tiene demasiadas responsabilidades y puede modularizarse."


@app.command(name="doctor")
def doctor(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git (por defecto: directorio actual)"),
    commits_limit: int = typer.Option(200, "--commits", "-c", help="Cantidad de commits a analizar"),
    html: bool = typer.Option(False, "--html", help="Genera y abre el reporte visual interactivo en HTML"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados (lockfiles, generated code)"),
    include_infra: bool = typer.Option(False, "--include-infra", help="Incluir archivos de infraestructura y scripts"),
    include_config: bool = typer.Option(False, "--include-config", help="Incluir manifiestos de paquetes (pubspec.yaml, package.json)"),
    include_l10n: bool = typer.Option(False, "--include-l10n", help="Incluir recursos de traducción (ej: .arb, .po)"),
):
    """
    🩺 [bold]Chequeo rápido de salud histórica (5 minutos)[/bold].
    
    Evalúa el estado del código fuente, calcula el puntaje de salud histórica (0-100),
    detecta los 5 archivos con mayor riesgo y genera recomendaciones inmediatas por tipo de archivo.
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
                exclude_config=not include_config,
                exclude_l10n=not include_l10n,
            )
            couplings = engine.detect_ghost_coupling(
                commits,
                exclude_generated=not include_generated,
                exclude_infra=not include_infra,
                exclude_config_pairs=not include_config,
                exclude_l10n_sync=not include_l10n,
            )
            bus_factors = engine.calculate_bus_factor(commits)
            health_score = engine.calculate_health_score(commits, hotspots, couplings, bus_factors)

        if not commits:
            console.print("[yellow]No se encontraron commits suficientes en este repositorio.[/yellow]")
            return

        color = "green" if health_score >= 80 else ("yellow" if health_score >= 50 else "red")

        console.print(f"\n[bold]Puntaje de Salud Histórica:[/bold] [{color} bold]{health_score} / 100[/{color} bold]")
        console.print(f"Commits analizados: [cyan]{len(commits)}[/cyan] | Archivos de código analizados: [cyan]{len(hotspots)}[/cyan]\n")

        # ── Tabla compacta de métricas (expand=True para aprovechar toda la pantalla) ──
        table = Table(title="🔥 Archivos de Código en Mayor Riesgo", border_style="blue", show_lines=True, expand=True)
        table.add_column("#", style="dim", justify="right", width=3)
        table.add_column("Archivo", style="cyan", ratio=4, no_wrap=False, overflow="fold")
        table.add_column("Tipo", style="dim", width=12)
        table.add_column("Commits", justify="right", width=8)
        table.add_column("Fixes", justify="right", width=6)
        table.add_column("Autores", justify="right", width=8)
        table.add_column("Propietario", style="magenta", ratio=3, no_wrap=False, overflow="fold")
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

        # ── Bus factor contextualizado según tamaño del equipo ──
        if bus_factors:
            top_b = bus_factors[0]
            total_devs = len(bus_factors)
            if total_devs <= 2:
                console.print(
                    f"\n[dim]👤 [bold]Contexto de Equipo:[/bold] Proyecto individual o reducido ({total_devs} autor(es)). "
                    f"{top_b.author_name} concentra el {top_b.ownership_percentage}% de los commits (comportamiento esperado).[/dim]"
                )
            elif top_b.ownership_percentage >= 70.0:
                console.print(
                    f"\n[bold red]⚠️  Riesgo de Bus Factor:[/bold red] "
                    f"[bold]{top_b.author_name}[/bold] concentra el [bold]{top_b.ownership_percentage}%[/bold] "
                    f"de los commits y es propietario de [bold]{top_b.files_owned_count}[/bold] archivo(s) en un equipo de {total_devs} desarrolladores. "
                    f"Si sale del proyecto, se pierde conocimiento crítico. "
                    f"[dim]→ Programa pair programming o revisiones cruzadas.[/dim]"
                )
            elif top_b.ownership_percentage >= 50.0:
                console.print(
                    f"\n[bold yellow]⚡ Bus Factor Moderado:[/bold yellow] "
                    f"[bold]{top_b.author_name}[/bold] lidera con {top_b.ownership_percentage}% de participación. "
                    f"[dim]→ Distribuye gradualmente el conocimiento.[/dim]"
                )

        # ── Acoplamientos ──
        if couplings:
            high_conf = sum(1 for c in couplings if c.confidence >= 0.8)
            console.print(
                f"\n[bold yellow]👻 {len(couplings)} acoplamiento(s) arquitectónico(s) detectado(s)[/bold yellow] "
                f"([bold red]{high_conf} con alta co-dependencia ≥80%[/bold red]). "
                f"Usa [cyan]repoarch coupling[/cyan] para ver el diagnóstico modular.\n"
            )
        else:
            console.print("\n[green]✓ No se detectaron acoplamientos fantasma significativos en la arquitectura.[/green]\n")

        if html:
            target_html = path.resolve() / "repoarch_report.html"
            recs = [
                f"Añadir tests unitarios y de integración prioritariamente a los {sum(1 for h in hotspots if h.risk_level == 'CRITICAL')} archivos críticos.",
                "Revisar los acoplamientos de alta co-dependencia y evaluar si requieren desacoplamiento modular.",
                "Programar sesiones de pair programming para distribuir el conocimiento entre autores.",
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
            HTMLExporter.export(report, target_html)
            console.print(f"[bold green]✓ Reporte interactivo HTML con scroll/sliders generado en:[/bold green] {target_html}\n")

        console.print("[dim]ℹ️  Solo se analiza código fuente real. Archivos generados, manifiestos y traducciones están excluidos.[/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error durante el diagnóstico:[/bold red] {e}")
        sys.exit(1)


@app.command(name="churn")
def churn(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    top: int = typer.Option(10, "--top", "-t", help="Cantidad de archivos a mostrar en el ranking de puntos calientes"),
    commits_limit: int = typer.Option(300, "--commits", "-c", help="Cantidad máxima de commits a analizar"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados"),
    include_infra: bool = typer.Option(False, "--include-infra", help="Incluir archivos de infraestructura y scripts"),
    include_config: bool = typer.Option(False, "--include-config", help="Incluir manifiestos de paquetes"),
    include_l10n: bool = typer.Option(False, "--include-l10n", help="Incluir recursos de traducción"),
):
    """
    🔥 [bold]Detecta Puntos Calientes (Hotspots) e Inestabilidad de Código[/bold].
    
    Identifica qué archivos cambian constantemente y concentran la mayor cantidad
    de correcciones de errores (bugfixes) y autores, indicando alta deuda técnica.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        hotspots = engine.calculate_hotspots(
            commits,
            exclude_generated=not include_generated,
            exclude_infra=not include_infra,
            exclude_config=not include_config,
            exclude_l10n=not include_l10n,
        )

        table = Table(title=f"🔥 Top {top} Puntos Calientes de Código (Code Churn)", border_style="blue", show_lines=True, expand=True)
        table.add_column("#", justify="right", style="dim", width=3)
        table.add_column("Archivo", style="cyan", ratio=4, no_wrap=False, overflow="fold")
        table.add_column("Tipo", style="dim", width=12)
        table.add_column("Commits", justify="right", width=8)
        table.add_column("Fixes", justify="right", width=6)
        table.add_column("Autores", justify="right", width=8)
        table.add_column("Churn", justify="right", width=8)
        table.add_column("Riesgo", justify="center", width=10)

        top_hotspots = hotspots[:top]
        for idx, h in enumerate(top_hotspots, start=1):
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            table.add_row(
                str(idx),
                h.file_path,
                get_file_role(h.file_path),
                str(h.commit_count),
                str(h.fix_count),
                str(h.authors_count),
                f"{h.churn_score}%",
                f"[{risk_color} bold]{h.risk_level}[/{risk_color} bold]",
            )
        console.print(table)

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

        console.print("[dim]ℹ️  Solo se analiza código fuente real. Usa --include-config o --include-l10n para ver manifiestos/traducciones.[/dim]")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="coupling")
def coupling(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    min_confidence: float = typer.Option(0.5, "--min-confidence", "-m", help="Umbral mínimo de co-dependencia (0.1 a 1.0; 0.8 = 80%)"),
    commits_limit: int = typer.Option(400, "--commits", "-c", help="Cantidad máxima de commits a analizar"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados"),
    include_infra: bool = typer.Option(False, "--include-infra", help="Incluir archivos de infraestructura"),
    include_config: bool = typer.Option(False, "--include-config", help="Incluir pares de manifiestos/configuración"),
):
    """
    👻 [bold]Descubre Acoplamientos Fantasma y Dependencias Ocultas[/bold].
    
    Encuentra pares de archivos que no tienen imports directos pero SIEMPRE
    se modifican juntos en los mismos commits, revelando dependencias no documentadas.
    """
    try:
        engine = GitEngine(path.resolve())
        commits = engine.extract_commits(max_count=commits_limit)
        couplings = engine.detect_ghost_coupling(
            commits,
            min_confidence=min_confidence,
            exclude_generated=not include_generated,
            exclude_infra=not include_infra,
            exclude_config_pairs=not include_config,
            exclude_l10n_sync=True,
        )

        if not couplings:
            console.print("[green]✓ No se detectaron acoplamientos fantasma por encima del umbral configurado.[/green]")
            return

        table = Table(title="👻 Acoplamientos Fantasma en Código Fuente", border_style="yellow", show_lines=True, expand=True)
        table.add_column("Archivo A", style="cyan", ratio=4, no_wrap=False, overflow="fold")
        table.add_column("Archivo B", style="magenta", ratio=4, no_wrap=False, overflow="fold")
        table.add_column("Co-Commits", justify="right", width=10)
        table.add_column("Co-dependencia", justify="right", width=16)
        table.add_column("Diagnóstico y Acción", style="dim", ratio=5, no_wrap=False, overflow="fold")

        for c in couplings[:15]:
            conf_color = "bold red" if c.confidence >= 0.8 else ("bold yellow" if c.confidence >= 0.6 else "bold green")
            conf_label = f"{int(c.confidence * 100)}% (Siempre)" if c.confidence >= 0.99 else f"{int(c.confidence * 100)}%"
            table.add_row(
                c.file_a,
                c.file_b,
                str(c.co_commit_count),
                f"[{conf_color}]{conf_label}[/{conf_color}]",
                c.explanation,
            )
        console.print(table)

        high_conf = [c for c in couplings if c.confidence >= 0.8]
        if high_conf:
            console.print(
                f"\n[bold red]🔴 {len(high_conf)} par(es) con co-dependencia crítica (≥80%):[/bold red] "
                f"cada vez que se modifica uno de estos archivos, casi siempre se tiene que modificar el otro obligatoriamente (fuerte acoplamiento oculto)."
            )
        console.print(
            "\n[dim]ℹ️  [bold]¿Qué significa Co-dependencia?[/bold] Mide qué porcentaje de las veces que se modifica el Archivo A también se modifica el Archivo B. "
            "Un 100% indica que están totalmente atados. Archivos generados, manifiestos y traducciones están excluidos para evitar falsos positivos.[/dim]"
        )
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="lore")
def lore(
    file_path: Optional[str] = typer.Argument(None, help="Ruta relativa del archivo a auditar (opcional: si se omite, analiza el hotspot más crítico)"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    commits_limit: int = typer.Option(300, "--commits", "-c", help="Cantidad máxima de commits a revisar en el historial del archivo")
):
    """
    📜 [bold]Reconstruye el Linaje Histórico y Contexto de Decisiones con IA[/bold].
    
    Explica cuándo nació el archivo, quién lo creó, cómo ha evolucionado a lo largo
    del tiempo, qué desarrolladores han participado y si sufre de regresiones frecuentes.
    """
    try:
        engine = GitEngine(path.resolve())
        all_commits = engine.extract_commits(max_count=commits_limit)

        if not file_path:
            hotspots = engine.calculate_hotspots(all_commits)
            if hotspots:
                file_path = hotspots[0].file_path
                console.print(f"[dim]ℹ️  No especificaste archivo. Analizando automáticamente el punto con mayor rotación: [bold cyan]{file_path}[/bold cyan][/dim]\n")
            else:
                console.print("[yellow]Debes especificar la ruta de un archivo para analizar su linaje: repoarch lore <ruta>[/yellow]")
                return

        file_commits = [c for c in all_commits if any(f.endswith(file_path) or f == file_path for f in c.files_changed)]
        if not file_commits:
            console.print(f"[yellow]No se encontraron commits en el historial para el archivo '{file_path}'.[/yellow]")
            return

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
    base: str = typer.Option("main", "--base", "-b", help="Rama base estable (contrato de referencia)"),
    target: str = typer.Option("develop", "--target", "-t", help="Rama objetivo con cambios a comparar"),
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git")
):
    """
    ⚡ [bold]Detecta Cambios que Rompen Contratos (Breaking Changes)[/bold].
    
    Compara dos ramas y analiza sintácticamente (mediante AST) si se eliminaron o modificaron
    funciones, métodos, clases o símbolos públicos que romperían integraciones.
    """
    try:
        engine = GitEngine(path.resolve())
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description=f"Comparando {base}...{target} y analizando ASTs...", total=None)
            changes = engine.compare_branches_for_breaking_changes(base_branch=base, target_branch=target)

        if not changes:
            console.print(f"[green]✓ No se detectaron roturas de contrato o firmas eliminadas entre {base} y {target}.[/green]")
            return

        table = Table(title=f"⚡ Breaking Changes Detectados ({base} ↔ {target})", border_style="red", show_lines=True, expand=True)
        table.add_column("Archivo", style="cyan", ratio=4, no_wrap=False, overflow="fold")
        table.add_column("Símbolo Afectado", style="bold red", ratio=3, no_wrap=False, overflow="fold")
        table.add_column("Descripción", style="dim", ratio=5, no_wrap=False, overflow="fold")

        for ch in changes:
            table.add_row(ch.file_path, ch.symbol_name, ch.description)
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)


@app.command(name="scan")
def scan(
    path: Path = typer.Option(Path("."), "--path", "-p", help="Ruta al repositorio Git"),
    commits_limit: int = typer.Option(400, "--commits", "-c", help="Cantidad de commits a inspeccionar en el historial"),
    export: Optional[Path] = typer.Option(None, "--export", "-e", help="Ruta de archivo para guardar el reporte (.html, .json, .md)"),
    html: bool = typer.Option(False, "--html", help="Genera y abre el reporte visual interactivo en HTML con scroll/sliders"),
    include_generated: bool = typer.Option(False, "--include-generated", help="Incluir archivos auto-generados"),
    include_infra: bool = typer.Option(False, "--include-infra", help="Incluir archivos de infraestructura y documentación"),
    include_config: bool = typer.Option(False, "--include-config", help="Incluir manifiestos de paquetes (pubspec.yaml, package.json)"),
    include_l10n: bool = typer.Option(False, "--include-l10n", help="Incluir recursos de traducción"),
):
    """
    📊 [bold]Auditoría forense integral y profunda[/bold].
    
    Realiza una radiografía completa del repositorio:
    • Top 10 Puntos Calientes de código (Code Churn).
    • Mapa de Acoplamientos Fantasma (Co-dependencias ocultas entre módulos).
    • Matriz de Propiedad de Código y Concentración (Bus Factor).
    • Plan Maestro de Mitigación de Deuda Técnica priorizado.
    """
    try:
        engine = GitEngine(path.resolve())
        console.print(Panel.fit(
            f"[bold blue]RepoArchaeology Scan[/bold blue] · Auditoría Forense Integral de [cyan]{path.resolve().name}[/cyan]",
            border_style="blue"
        ))

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
            progress.add_task(description="Extrayendo commits, calculando ASTs, hotspots y correlaciones...", total=None)
            commits = engine.extract_commits(max_count=commits_limit)
            hotspots = engine.calculate_hotspots(
                commits,
                exclude_generated=not include_generated,
                exclude_infra=not include_infra,
                exclude_config=not include_config,
                exclude_l10n=not include_l10n,
            )
            couplings = engine.detect_ghost_coupling(
                commits,
                exclude_generated=not include_generated,
                exclude_infra=not include_infra,
                exclude_config_pairs=not include_config,
                exclude_l10n_sync=not include_l10n,
            )
            bus_factors = engine.calculate_bus_factor(commits)
            health_score = engine.calculate_health_score(commits, hotspots, couplings, bus_factors)

        if not commits:
            console.print("[yellow]No se encontraron commits suficientes en este repositorio.[/yellow]")
            return

        critical_hotspots = [h for h in hotspots if h.risk_level == "CRITICAL"]
        high_couplings = [c for c in couplings if c.confidence >= 0.8]
        total_fixes = sum(1 for c in commits if c.is_fix)
        fix_pct = round((total_fixes / len(commits)) * 100, 1)

        color = "green" if health_score >= 80 else ("yellow" if health_score >= 50 else "red")

        # ── Resumen de Métricas Globales ──
        console.print(f"\n[bold]Puntaje de Salud Histórica:[/bold] [{color} bold]{health_score} / 100[/{color} bold]")
        console.print(
            f"Commits: [cyan]{len(commits)}[/cyan] ([dim]{fix_pct}% fixes[/dim]) | "
            f"Archivos: [cyan]{len(hotspots)}[/cyan] ([red]{len(critical_hotspots)} críticos[/red]) | "
            f"Acoplamientos Ocultos: [cyan]{len(couplings)}[/cyan] ([red]{len(high_couplings)} críticos[/red]) | "
            f"Autores: [cyan]{len(bus_factors)}[/cyan]\n"
        )

        # ── 1. Tabla de Hotspots (Top 10) ──
        table_hot = Table(title="🔥 1. Puntos Calientes de Mayor Riesgo (Top Hotspots)", border_style="blue", show_lines=True, expand=True)
        table_hot.add_column("#", justify="right", style="dim", width=3)
        table_hot.add_column("Archivo", style="cyan", ratio=4, no_wrap=False, overflow="fold")
        table_hot.add_column("Tipo", style="dim", width=12)
        table_hot.add_column("Commits", justify="right", width=8)
        table_hot.add_column("Fixes", justify="right", width=6)
        table_hot.add_column("Autores", justify="right", width=8)
        table_hot.add_column("Propietario", style="magenta", ratio=2, no_wrap=False, overflow="fold")
        table_hot.add_column("Riesgo", justify="center", width=10)

        for idx, h in enumerate(hotspots[:10], start=1):
            risk_color = "red" if h.risk_level == "CRITICAL" else ("yellow" if h.risk_level == "HIGH" else "green")
            table_hot.add_row(
                str(idx),
                h.file_path,
                get_file_role(h.file_path),
                str(h.commit_count),
                str(h.fix_count),
                str(h.authors_count),
                f"{h.top_author} ({h.top_author_percentage}%)",
                f"[{risk_color} bold]{h.risk_level}[/{risk_color} bold]",
            )
        console.print(table_hot)

        # ── 2. Tabla de Acoplamientos Fantasma (Top 10) ──
        if couplings:
            console.print("")
            table_coup = Table(title="👻 2. Acoplamientos Fantasma y Co-dependencias Críticas", border_style="yellow", show_lines=True, expand=True)
            table_coup.add_column("Archivo A", style="cyan", ratio=4, no_wrap=False, overflow="fold")
            table_coup.add_column("Archivo B", style="magenta", ratio=4, no_wrap=False, overflow="fold")
            table_coup.add_column("Co-Commits", justify="right", width=10)
            table_coup.add_column("Co-dependencia", justify="right", width=16)
            table_coup.add_column("Diagnóstico y Acción", style="dim", ratio=5, no_wrap=False, overflow="fold")

            for c in couplings[:10]:
                conf_color = "bold red" if c.confidence >= 0.8 else ("bold yellow" if c.confidence >= 0.6 else "bold green")
                conf_label = f"{int(c.confidence * 100)}% (Siempre)" if c.confidence >= 0.99 else f"{int(c.confidence * 100)}%"
                table_coup.add_row(
                    c.file_a,
                    c.file_b,
                    str(c.co_commit_count),
                    f"[{conf_color}]{conf_label}[/{conf_color}]",
                    c.explanation,
                )
            console.print(table_coup)

        # ── 3. Tabla de Bus Factor y Propiedad de Código ──
        if bus_factors:
            console.print("")
            table_bus = Table(title="👤 3. Concentración de Propiedad de Código (Bus Factor)", border_style="magenta", show_lines=True, expand=True)
            table_bus.add_column("Autor / Desarrollador", style="cyan", ratio=3)
            table_bus.add_column("Commits", justify="right", width=10)
            table_bus.add_column("% Participación", justify="right", width=16)
            table_bus.add_column("Archivos Propios", justify="right", width=16)
            table_bus.add_column("Estado de Riesgo", justify="center", ratio=2)

            for b in bus_factors[:8]:
                if b.ownership_percentage >= 70 and len(bus_factors) > 2:
                    st_color, st_label = "bold red", "CRÍTICO (Concentrado)"
                elif b.ownership_percentage >= 40:
                    st_color, st_label = "bold yellow", "Principal"
                else:
                    st_color, st_label = "green", "Colaborador"

                table_bus.add_row(
                    b.author_name,
                    str(b.commit_count),
                    f"{b.ownership_percentage}%",
                    f"{b.files_owned_count} archivo(s)",
                    f"[{st_color}]{st_label}[/{st_color}]"
                )
            console.print(table_bus)

        # ── 4. Plan de Acción y Deuda Técnica Consolidada ──
        recs = [
            f"Prioridad 1: Refactorizar y añadir tests a los [bold cyan]{len(critical_hotspots)} archivo(s) con rotación crítica[/bold cyan].",
            f"Prioridad 2: Desacoplar los [bold yellow]{len(high_couplings)} pares con co-dependencia ≥80%[/bold yellow] para evitar roturas invisibles.",
            "Prioridad 3: Distribuir conocimiento mediante revisiones de código y pair programming.",
            "Prioridad 4: Mantener la exclusión de artefactos generados para preservar métricas limpias en CI.",
        ]
        console.print(Panel(
            "\n".join(f"  • {r}" for r in recs),
            title="📋 4. Plan de Mitigación de Deuda Técnica",
            border_style="green",
            padding=(0, 1),
        ))

        # ── Exportación ──
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
            console.print(f"\n[bold green]✓ Reporte completo exportado a:[/bold green] {export.resolve()}")
        elif html:
            target_html = path.resolve() / "repoarch_report.html"
            HTMLExporter.export(report, target_html)
            console.print(f"\n[bold green]✓ Reporte interactivo HTML con scroll/sliders generado en:[/bold green] {target_html}")
        else:
            console.print("\n[dim]💡 Tip: Puedes exportar este informe completo con: [cyan]repoarch scan --html[/cyan] o [cyan]repoarch scan --export reporte.json[/cyan][/dim]\n")

    except Exception as e:
        console.print(f"[bold red]Error durante el escaneo:[/bold red] {e}")
        sys.exit(1)


def main():
    app()


if __name__ == "__main__":
    main()
