"""
Sistema de comprobación y actualización automática de RepoArchaeology.
"""
import os
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()
CACHE_FILE = Path.home() / ".local" / "share" / "repoarchaeology" / ".update_check.json"
CHECK_INTERVAL_SECONDS = 43200  # Verificar máximo 1 vez cada 12 horas para no ralentizar la CLI


def get_repo_dir() -> Optional[Path]:
    """Obtiene la ruta del repositorio fuente instalado."""
    # 1. Si estamos ejecutando desde el código fuente
    current_dir = Path(__file__).resolve().parent.parent.parent
    if (current_dir / ".git").exists():
        return current_dir
    # 2. Ruta por defecto en Proyectos
    default_proj = Path.home() / "Proyectos" / "RepoArchaeology"
    if (default_proj / ".git").exists():
        return default_proj
    return None


def should_check_update() -> bool:
    """Verifica si ha pasado el tiempo prudente para consultar actualizaciones."""
    try:
        if not CACHE_FILE.exists():
            return True
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        last_check = data.get("last_check", 0)
        return (time.time() - last_check) > CHECK_INTERVAL_SECONDS
    except Exception:
        return True


def record_update_check(has_update: bool = False) -> None:
    """Guarda la marca de tiempo de la última verificación."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps({"last_check": time.time(), "has_update": has_update}),
            encoding="utf-8"
        )
    except Exception:
        pass


def check_for_updates_available() -> Tuple[bool, str]:
    """Consulta al remote Git si hay nuevos commits en la rama actual."""
    repo_dir = get_repo_dir()
    if not repo_dir:
        return False, ""
        
    try:
        # Fetch silencioso con timeout corto
        subprocess.run(
            ["git", "-C", str(repo_dir), "fetch", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False
        )
        
        # Comparar HEAD local con @{u} (upstream)
        status_out = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-list", "HEAD..@{u}", "--count"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
            check=False
        )
        
        if status_out.returncode == 0:
            count = int(status_out.stdout.strip() or "0")
            if count > 0:
                record_update_check(has_update=True)
                return True, f"Hay {count} cambio(s) nuevo(s) disponible(s)."
    except Exception:
        pass
        
    record_update_check(has_update=False)
    return False, ""


def perform_update() -> bool:
    """Ejecuta la actualización en caliente del repositorio y el entorno virtual."""
    repo_dir = get_repo_dir()
    if not repo_dir:
        console.print("[red]No se encontró el repositorio fuente de RepoArchaeology para actualizar.[/red]")
        return False
        
    venv_python = Path.home() / ".local" / "share" / "repoarchaeology" / "venv" / "bin" / "python"
    venv_pip = Path.home() / ".local" / "share" / "repoarchaeology" / "venv" / "bin" / "pip"
    
    console.print(Panel("[bold blue]Iniciando actualización de RepoArchaeology...[/bold blue]", border_style="blue"))
    
    try:
        # 1. Git pull
        console.print("[dim]Descargando cambios desde el repositorio Git...[/dim]")
        pull_res = subprocess.run(
            ["git", "-C", str(repo_dir), "pull", "--quiet"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False
        )
        if pull_res.returncode != 0:
            console.print(f"[bold yellow]Aviso al hacer pull:[/bold yellow] {pull_res.stderr.strip()}")
            
        # 2. Pip update
        if venv_pip.exists():
            console.print("[dim]Actualizando dependencias en el entorno virtual aislado...[/dim]")
            subprocess.run(
                [str(venv_pip), "install", "--upgrade", "--quiet", "--no-warn-script-location", "-e", f"{str(repo_dir)}[tui,ai]"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=60,
                check=False
            )
            
        console.print("[bold green]✓ RepoArchaeology se ha actualizado exitosamente a la última versión.[/bold green]\n")
        record_update_check(has_update=False)
        return True
    except Exception as e:
        console.print(f"[bold red]Error durante la actualización:[/bold red] {e}")
        return False


def prompt_auto_update_if_needed() -> None:
    """Comprueba y pregunta interactivamente al usuario si desea actualizar."""
    # Evitar comprobar si estamos redirigiendo salidas no interactivas
    if not sys.stdout.isatty():
        return
        
    if not should_check_update():
        return
        
    available, msg = check_for_updates_available()
    if available:
        console.print(Panel(
            f"🚀 [bold cyan]¡Hay una nueva actualización disponible de RepoArchaeology![/bold cyan]\n"
            f"[dim]{msg}[/dim]\n\n"
            f"¿Deseas actualizar ahora en un solo paso?",
            title="🔔 Actualización Disponible",
            border_style="yellow"
        ))
        
        try:
            choice = Confirm.ask("¿Actualizar RepoArchaeology ahora?", default=False)
            if choice:
                perform_update()
        except (KeyboardInterrupt, EOFError):
            pass
