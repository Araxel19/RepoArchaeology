"""
Sistema amigable e inteligente de comprobación y actualización de RepoArchaeology.
"""
import os
import re
import sys
import time
import json
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from repoarchaeology import __version__

console = Console()
CACHE_FILE = Path.home() / ".local" / "share" / "repoarchaeology" / ".update_check.json"
CHECK_INTERVAL_SECONDS = 43200  # Máximo 1 verificación cada 12 horas en comandos normales


def get_repo_dir() -> Optional[Path]:
    """Obtiene la ruta del repositorio fuente instalado."""
    current_dir = Path(__file__).resolve().parent.parent.parent
    if (current_dir / ".git").exists():
        return current_dir
    default_proj = Path.home() / "Proyectos" / "RepoArchaeology"
    if (default_proj / ".git").exists():
        return default_proj
    return None


def get_remote_version(repo_dir: Path) -> Optional[str]:
    """Extrae el número de versión disponible en origin/main."""
    try:
        res = subprocess.run(
            ["git", "-C", str(repo_dir), "show", "origin/main:repoarchaeology/__init__.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=4,
            check=False
        )
        if res.returncode == 0:
            match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', res.stdout)
            if match:
                return match.group(1)
    except Exception:
        pass
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


def record_update_check(has_update: bool = False, remote_ver: str = "") -> None:
    """Guarda la marca de tiempo de la última verificación."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(
            json.dumps({
                "last_check": time.time(),
                "has_update": has_update,
                "remote_version": remote_ver
            }),
            encoding="utf-8"
        )
    except Exception:
        pass


def check_for_updates_available() -> Tuple[bool, str, str, int]:
    """
    Consulta si hay una versión o mejoras nuevas en GitHub.
    Retorna: (hay_actualizacion, version_actual, version_remota, conteo_mejoras)
    """
    repo_dir = get_repo_dir()
    current_ver = f"v{__version__}"
    
    if not repo_dir:
        return False, current_ver, current_ver, 0
        
    try:
        # Fetch silencioso de origin/main
        subprocess.run(
            ["git", "-C", str(repo_dir), "fetch", "origin", "main", "--quiet"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False
        )
        
        status_out = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-list", "HEAD..origin/main", "--count"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=4,
            check=False
        )
        
        raw_remote_ver = get_remote_version(repo_dir)
        remote_ver = f"v{raw_remote_ver}" if raw_remote_ver else current_ver
        
        if status_out.returncode == 0:
            count = int(status_out.stdout.strip() or "0")
            if count > 0:
                record_update_check(has_update=True, remote_ver=remote_ver)
                return True, current_ver, remote_ver, count
    except Exception:
        pass
        
    record_update_check(has_update=False, remote_ver=current_ver)
    return False, current_ver, current_ver, 0


def perform_update() -> bool:
    """Ejecuta la actualización del software con mensajes amigables y claros."""
    repo_dir = get_repo_dir()
    current_ver = f"v{__version__}"
    
    if not repo_dir:
        console.print("[red]No se encontró la instalación principal de RepoArchaeology para actualizar.[/red]")
        return False
        
    venv_pip = Path.home() / ".local" / "share" / "repoarchaeology" / "venv" / "bin" / "pip"
    
    # 1. Comprobar si hay cambios
    has_update, cur_v, rem_v, count = check_for_updates_available()
    
    if not has_update:
        console.print(Panel(
            f"✅ [bold green]¡Todo está al día![/bold green]\n\n"
            f"Ya estás utilizando la versión más reciente de [bold cyan]RepoArchaeology[/bold cyan] ([bold green]{current_ver}[/bold green]).",
            title="✨ Estado del Sistema",
            border_style="green"
        ))
        return True

    # 2. Si hay actualización, proceder
    version_diff = f"[bold yellow]{cur_v}[/bold yellow] ➔ [bold green]{rem_v}[/bold green]" if cur_v != rem_v else f"[bold green]{rem_v}[/bold green] ([dim]{count} mejoras nuevas[/dim])"
    
    console.print(Panel(
        f"🔄 [bold blue]Actualizando RepoArchaeology...[/bold blue]\n"
        f"Versión: {version_diff}",
        border_style="blue"
    ))
    
    try:
        console.print("[dim]⬇️  Descargando las últimas mejoras y novedades...[/dim]")
        pull_cmd = ["git", "-C", str(repo_dir), "pull", "origin", "main", "--ff-only", "--quiet"]
        subprocess.run(
            pull_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False
        )
        
        if venv_pip.exists():
            console.print("[dim]⚙️  Configurando los componentes del sistema...[/dim]")
            subprocess.run(
                [str(venv_pip), "install", "--upgrade", "--quiet", "--no-warn-script-location", "-e", f"{str(repo_dir)}[tui,ai]"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
                check=False
            )
            
        console.print(f"\n🎉 [bold green]¡Listo! RepoArchaeology se ha actualizado con éxito a la versión {rem_v}.[/bold green]\n")
        record_update_check(has_update=False, remote_ver=rem_v)
        return True
    except Exception as e:
        console.print(f"[bold red]Ocurrió un detalle al actualizar:[/bold red] {e}")
        return False


def prompt_auto_update_if_needed() -> None:
    """Comprueba en segundo plano y pregunta de forma amigable si desea actualizar."""
    if not sys.stdout.isatty():
        return
        
    if not should_check_update():
        return
        
    has_update, cur_v, rem_v, count = check_for_updates_available()
    if has_update:
        version_text = f"Versión actual: [bold yellow]{cur_v}[/bold yellow]  ➔  Nueva versión: [bold green]{rem_v}[/bold green]" if cur_v != rem_v else f"Nueva versión: [bold green]{rem_v}[/bold green]"
        
        console.print(Panel(
            f"🚀 [bold cyan]¡Hay una nueva actualización disponible de RepoArchaeology![/bold cyan]\n\n"
            f"{version_text}\n"
            f"[dim]Incluye {count} mejora(s) de estabilidad y nuevas funciones.[/dim]\n\n"
            f"¿Deseas actualizar ahora en un solo clic?",
            title="🔔 Actualización Disponible",
            border_style="yellow"
        ))
        
        try:
            choice = Confirm.ask("¿Actualizar RepoArchaeology ahora?", default=False)
            if choice:
                perform_update()
        except (KeyboardInterrupt, EOFError):
            pass
