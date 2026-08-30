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
CHECK_INTERVAL_SECONDS = 43200  # Máximo 1 verificación cada 12 horas para no ralentizar la CLI


def get_repo_dir() -> Optional[Path]:
    """Obtiene la ruta del repositorio fuente instalado."""
    current_dir = Path(__file__).resolve().parent.parent.parent
    if (current_dir / ".git").exists():
        return current_dir
    default_proj = Path.home() / "Proyectos" / "RepoArchaeology"
    if (default_proj / ".git").exists():
        return default_proj
    return None


def get_current_branch(repo_dir: Path) -> str:
    """Detecta la rama actual activa."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=3,
            check=False
        )
        return res.stdout.strip() or "main"
    except Exception:
        return "main"


def has_upstream_configured(repo_dir: Path) -> bool:
    """Verifica si la rama actual tiene un upstream remoto vinculado."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "@{u}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
            check=False
        )
        return res.returncode == 0
    except Exception:
        return False


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
        # Fetch silencioso
        subprocess.run(
            ["git", "-C", str(repo_dir), "fetch", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False
        )
        
        branch = get_current_branch(repo_dir)
        target_ref = "@{u}" if has_upstream_configured(repo_dir) else f"origin/{branch}"
        
        status_out = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-list", f"HEAD..{target_ref}", "--count"],
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
                return True, f"Hay {count} cambio(s) nuevo(s) en GitHub."
    except Exception:
        pass
        
    record_update_check(has_update=False)
    return False, ""


def perform_update() -> bool:
    """Ejecuta la actualización del repositorio y el entorno virtual."""
    repo_dir = get_repo_dir()
    if not repo_dir:
        console.print("[red]No se encontró el repositorio fuente de RepoArchaeology para actualizar.[/red]")
        return False
        
    venv_pip = Path.home() / ".local" / "share" / "repoarchaeology" / "venv" / "bin" / "pip"
    branch = get_current_branch(repo_dir)
    
    console.print(Panel("[bold blue]Iniciando actualización de RepoArchaeology...[/bold blue]", border_style="blue"))
    
    try:
        # 1. Git pull con manejo de rama
        console.print(f"[dim]Descargando cambios desde el repositorio Git (rama: {branch})...[/dim]")
        
        if has_upstream_configured(repo_dir):
            pull_cmd = ["git", "-C", str(repo_dir), "pull", "--ff-only", "--quiet"]
        else:
            pull_cmd = ["git", "-C", str(repo_dir), "pull", "origin", branch, "--ff-only", "--quiet"]
            
        pull_res = subprocess.run(
            pull_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False
        )
        
        if pull_res.returncode != 0:
            err = pull_res.stderr.strip()
            if any(k in err.lower() for k in ["couldn't find remote", "no tracking", "diverg", "reconcil", "not on a branch"]):
                console.print(f"[dim]Nota: Repositorio local sincronizado (rama: {branch}).[/dim]")
            else:
                console.print(f"[bold yellow]Aviso Git:[/bold yellow] {err}")
            
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
