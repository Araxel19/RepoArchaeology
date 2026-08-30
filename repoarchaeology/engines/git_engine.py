"""
Motor de análisis forense y minería de Git de alto rendimiento.
Incluye filtrado inteligente de archivos generados/automáticos para análisis más precisos.
"""
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict
import re

from repoarchaeology.core.models import CommitInfo, FileHotspot, CouplingPair, AuthorBusFactor, BreakingChangeInfo
from repoarchaeology.core.security import redact_secrets
from repoarchaeology.engines.ast_engine import ASTEngine


# ─────────────────────────────────────────────────────────────────────────────
# Patrones de archivos auto-generados, de configuración de infraestructura
# y de soporte que NO aportan valor al análisis de código fuente.
# ─────────────────────────────────────────────────────────────────────────────
GENERATED_FILE_PATTERNS: List[re.Pattern] = [
    # Lock / dependency snapshot files
    re.compile(r"(^|/)pubspec\.lock$"),
    re.compile(r"(^|/)package-lock\.json$"),
    re.compile(r"(^|/)yarn\.lock$"),
    re.compile(r"(^|/)Cargo\.lock$"),
    re.compile(r"(^|/)Gemfile\.lock$"),
    re.compile(r"(^|/)poetry\.lock$"),
    re.compile(r"(^|/)composer\.lock$"),
    re.compile(r"(^|/)pnpm-lock\.yaml$"),
    re.compile(r"(^|/)go\.sum$"),
    re.compile(r"(^|/)flake\.lock$"),
    re.compile(r"(^|/)mix\.lock$"),

    # Flutter / Dart generated localization & build artifacts
    re.compile(r"app_localizations\.dart$"),
    re.compile(r"app_localizations_[a-z_]+\.dart$"),
    re.compile(r"\.g\.dart$"),
    re.compile(r"\.freezed\.dart$"),
    re.compile(r"\.mocks\.dart$"),
    re.compile(r"(^|/)build/"),

    # JS / TS generated bundles and type maps
    re.compile(r"\.min\.js$"),
    re.compile(r"\.map$"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)\.next/"),
    re.compile(r"(^|/)out/"),

    # Python generated
    re.compile(r"\.pyc$"),
    re.compile(r"(^|/)__pycache__/"),
    re.compile(r"(^|/)\.mypy_cache/"),
    re.compile(r"(^|/)htmlcov/"),
    re.compile(r"(^|/)\.coverage"),

    # Documentation and changelog auto-gen
    re.compile(r"(^|/)CHANGELOG\.md$"),
    re.compile(r"(^|/)CHANGELOG\.rst$"),

    # IDE and tooling metadata
    re.compile(r"(^|/)\.idea/"),
    re.compile(r"(^|/)\.vscode/"),
    re.compile(r"(^|/)\.dart_tool/"),
    re.compile(r"(^|/)\.flutter-plugins"),
    re.compile(r"(^|/)\.flutter-plugins-dependencies"),
    re.compile(r"\.iml$"),

    # Generic data and image dumps
    re.compile(r"\.(png|jpg|jpeg|gif|ico|svg|webp|woff|woff2|ttf|eot|otf)$"),
    re.compile(r"\.(pdf|xlsx|xls|doc|docx|ppt|pptx|csv|tsv)$"),
    re.compile(r"\.(mp4|mp3|wav|ogg|avi|mov|webm)$"),
    re.compile(r"\.(zip|tar\.gz|tar\.bz2|rar|7z)$"),
    re.compile(r"\.(bin|exe|dll|so|dylib|wasm)$"),
]

# Archivos de infraestructura que cambian pero no representan deuda técnica del código
INFRA_PATTERNS: List[re.Pattern] = [
    re.compile(r"(^|/)README(\.md|\.rst|\.txt)?$", re.IGNORECASE),
    re.compile(r"(^|/)LICENSE(\.md|\.txt)?$", re.IGNORECASE),
    re.compile(r"(^|/)CONTRIBUTING(\.md|\.rst)?$", re.IGNORECASE),
    re.compile(r"(^|/)\.gitignore$"),
    re.compile(r"(^|/)\.gitattributes$"),
    re.compile(r"(^|/)Makefile$"),
    re.compile(r"(^|/)Dockerfile$"),
    re.compile(r"(^|/)docker-compose\.ya?ml$"),
    re.compile(r"(^|/)\.env\.example$"),
    re.compile(r"(^|/)\.github/"),
    re.compile(r"(^|/)\.gitlab-ci\.ya?ml$"),
    re.compile(r"(^|/)\.(travis|circleci|jenkins)\.ya?ml$"),
]

# Archivos de configuración de alto nivel que pueden ser válidos para hotspot en proyectos pequeños,
# pero que en proyectos grandes son normales de cambiar frecuentemente.
HIGH_LEVEL_CONFIG_PATTERNS: List[re.Pattern] = [
    re.compile(r"(^|/)pubspec\.yaml$"),
    re.compile(r"(^|/)package\.json$"),
    re.compile(r"(^|/)pyproject\.toml$"),
    re.compile(r"(^|/)setup\.cfg$"),
    re.compile(r"(^|/)setup\.py$"),
    re.compile(r"(^|/)tsconfig\.json$"),
    re.compile(r"(^|/)vite\.config\.(ts|js)$"),
    re.compile(r"(^|/)webpack\.config\.(ts|js)$"),
    re.compile(r"(^|/)next\.config\.(ts|js|mjs)$"),
    re.compile(r"(^|/)tailwind\.config\.(ts|js)$"),
    re.compile(r"(^|/)Cargo\.toml$"),
    re.compile(r"(^|/)go\.mod$"),
]

# Etiquetas de rol para diagnósticos enriquecidos
ROLE_LABELS: Dict[str, str] = {
    ".dart":  "Componente Flutter/Dart",
    ".py":    "Módulo Python",
    ".js":    "Módulo JavaScript",
    ".jsx":   "Componente React",
    ".ts":    "Módulo TypeScript",
    ".tsx":   "Componente React/TS",
    ".go":    "Paquete Go",
    ".rs":    "Módulo Rust",
    ".java":  "Clase Java",
    ".kt":    "Archivo Kotlin",
    ".swift": "Archivo Swift",
    ".vue":   "Componente Vue",
    ".svelte":"Componente Svelte",
    ".yaml":  "Configuración YAML",
    ".toml":  "Configuración TOML",
    ".json":  "Configuración JSON",
    ".arb":   "Recurso de Localización",
    ".sql":   "Esquema/Query SQL",
    ".sh":    "Script de Shell",
    ".html":  "Plantilla HTML",
    ".css":   "Hoja de Estilos",
    ".scss":  "Hoja de Estilos SCSS",
}


def is_auto_generated(file_path: str) -> bool:
    """Detecta si un archivo es generado automáticamente (no escrito a mano)."""
    for pattern in GENERATED_FILE_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def is_infra_only(file_path: str) -> bool:
    """Detecta si un archivo es solo infraestructura/documentación del repo."""
    for pattern in INFRA_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def is_high_level_config(file_path: str) -> bool:
    """Detecta si un archivo es configuración de alto nivel del proyecto."""
    for pattern in HIGH_LEVEL_CONFIG_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def should_exclude_from_analysis(file_path: str) -> bool:
    """Decide si un archivo debe excluirse del análisis de calidad de código."""
    return is_auto_generated(file_path) or is_infra_only(file_path)


def get_file_role(file_path: str) -> str:
    """Devuelve un rol semántico legible para el archivo según su extensión."""
    suffix = Path(file_path).suffix.lower()
    return ROLE_LABELS.get(suffix, f"Archivo {suffix}" if suffix else "Archivo de código")


def generate_coupling_insight(fa: str, fb: str, co_count: int, confidence: float) -> str:
    """
    Genera un diagnóstico enriquecido y accionable para el acoplamiento detectado.
    Va más allá de la extensión y evalúa el patrón arquitectónico subyacente.
    """
    ext_a = Path(fa).suffix.lower()
    ext_b = Path(fb).suffix.lower()
    name_a = Path(fa).name
    name_b = Path(fb).name
    dir_a = str(Path(fa).parent)
    dir_b = str(Path(fb).parent)

    # Detección semántica por nombre
    if ("model" in fa.lower() or "domain" in fa.lower()) and ("repo" in fb.lower() or "data" in fb.lower()):
        return "Dependencia directa modelo→repositorio. Evalúa si el dominio filtra lógica de persistencia."
    if ("model" in fb.lower() or "domain" in fb.lower()) and ("repo" in fa.lower() or "data" in fa.lower()):
        return "Dependencia directa modelo→repositorio. Evalúa si el dominio filtra lógica de persistencia."

    if ("presenter" in fa.lower() or "viewmodel" in fa.lower()) and ("page" in fb.lower() or "screen" in fb.lower() or "view" in fb.lower()):
        return "Presenter/ViewModel fuertemente acoplado a su vista. Verifica separación de responsabilidades."
    if ("presenter" in fb.lower() or "viewmodel" in fb.lower()) and ("page" in fa.lower() or "screen" in fa.lower() or "view" in fa.lower()):
        return "Presenter/ViewModel fuertemente acoplado a su vista. Verifica separación de responsabilidades."

    if "controller" in fa.lower() and "route" in fb.lower():
        return "Controlador y ruta cambian juntos. Considera separar la definición de rutas del controlador."
    if "controller" in fb.lower() and "route" in fa.lower():
        return "Controlador y ruta cambian juntos. Considera separar la definición de rutas del controlador."

    if "service" in fa.lower() and "model" in fb.lower():
        return "Servicio vinculado a modelo. Si es frecuente, considera un UseCase o DTO intermedio."
    if "service" in fb.lower() and "model" in fa.lower():
        return "Servicio vinculado a modelo. Si es frecuente, considera un UseCase o DTO intermedio."

    if "test" in fa.lower() or "test" in fb.lower() or "_test." in fa or "_test." in fb:
        return "Archivo de test acoplado al módulo. Es esperable, verifica que el test cubre todos los casos."

    # Detección de patrón de localización
    if ext_a in (".arb",) or ext_b in (".arb",):
        return "Archivos de localización que cambian juntos. Normal si se añaden textos; verifica que no falten traducciones."

    # Por capas arquitectónicas
    if dir_a == dir_b:
        parts = dir_a.lower().split("/")
        if "data" in parts or "datasource" in parts:
            return "Dos archivos de la capa de datos cambian juntos. Riesgo de lógica de negocio mezclada con persistencia."
        if "domain" in parts:
            return "Dos entidades/casos de uso cambian en sincronía. Evalúa si comparten responsabilidad o pueden unificarse."
        if "presentation" in parts or "presenter" in parts or "ui" in parts:
            return "Dos componentes de UI cambian juntos. Considera extraer lógica compartida a un widget/componente base."
        if "service" in parts or "services" in parts:
            return "Dos servicios se modifican en conjunto. Pueden compartir dependencias o lógica transversal."
        if "feature" in parts or "features" in parts:
            return "Co-modificación dentro de la misma feature. Normal si es la misma historia de usuario; verifica cohesión."
        return "Co-modificación en la misma carpeta. Evalúa si los archivos pueden combinarse o si comparten demasiada lógica."

    # Capas distintas
    layers_a = set(dir_a.lower().split("/"))
    layers_b = set(dir_b.lower().split("/"))
    cross_layer_markers = {"data", "domain", "presentation", "service", "ui", "routes", "api", "models"}
    a_layer = layers_a & cross_layer_markers
    b_layer = layers_b & cross_layer_markers

    if a_layer and b_layer and a_layer != b_layer:
        la = next(iter(a_layer))
        lb = next(iter(b_layer))
        return f"Acoplamiento entre capas '{la}' y '{lb}'. Verifica que no hay dependencias invertidas."

    if ext_a != ext_b:
        return f"Acoplamiento cross-tecnología ({ext_a} ↔ {ext_b}). Podría indicar lógica duplicada o falta de abstracción."

    return "Co-modificación recurrente. Considera extraer lógica común o documentar la dependencia explícitamente."


class GitEngine:
    """Extractor y procesador forense sobre repositorios Git."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._validate_repo()

    def _validate_repo(self) -> None:
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"El directorio '{self.repo_path}' no contiene un repositorio Git válido.")

    def _run_git(self, args: List[str]) -> str:
        """Ejecuta un comando git de forma segura con lista de argumentos y timeout."""
        cmd = ["git", "-C", str(self.repo_path)] + args
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=45,
            check=False
        )
        if result.returncode != 0:
            err_msg = result.stderr.strip()
            if "does not have any commits yet" in err_msg or "unknown revision" in err_msg:
                return ""
            raise RuntimeError(f"Error al ejecutar git: {err_msg}")
        return result.stdout

    def extract_commits(self, max_count: int = 500) -> List[CommitInfo]:
        """Extrae commits estructurados con detección de tipo y archivos afectados."""
        delim = "__REPOARCH_COMMIT__"
        format_str = f"{delim}%x1f%H%x1f%h%x1f%an%x1f%ae%x1f%at%x1f%s"
        log_out = self._run_git([
            "log",
            f"-n{max_count}",
            f"--format={format_str}",
            "--name-only"
        ])

        if not log_out.strip():
            return []

        commits: List[CommitInfo] = []
        raw_entries = log_out.split(delim + "\x1f")

        for entry in raw_entries:
            if not entry.strip():
                continue
            lines = entry.strip().split("\n")
            header = lines[0].split("\x1f")
            if len(header) < 6:
                continue

            h, sh, author, email, ts, msg = header[0], header[1], header[2], header[3], header[4], header[5]
            files = [f.strip() for f in lines[1:] if f.strip() and not f.startswith(".git/")]

            msg_clean = redact_secrets(msg)
            msg_lower = msg_clean.lower()

            is_fix = any(w in msg_lower for w in ["fix", "bug", "hotfix", "patch", "error", "issue", "repair", "corrige", "resolv"])
            is_refactor = any(w in msg_lower for w in ["refactor", "cleanup", "reorganize", "restructure", "clean", "rewrite"])
            is_breaking = any(w in msg_lower for w in ["breaking", "breaking change", "deprecat", "incompatible"])

            try:
                commit_date = datetime.fromtimestamp(int(ts))
            except Exception:
                commit_date = datetime.utcnow()

            commits.append(CommitInfo(
                hash=h,
                short_hash=sh,
                author_name=author,
                author_email=email,
                date=commit_date,
                message=msg_clean,
                files_changed=files,
                is_fix=is_fix,
                is_refactor=is_refactor,
                is_breaking=is_breaking
            ))

        return commits

    def calculate_hotspots(
        self,
        commits: List[CommitInfo],
        exclude_generated: bool = True,
        exclude_infra: bool = True,
    ) -> List[FileHotspot]:
        """
        Calcula la métrica de Code Churn ponderada con fix rate y autor principal.
        Filtra automáticamente archivos generados e infraestructura para centrarse
        en código fuente real escrito por humanos.
        """
        if not commits:
            return []

        file_commits: Dict[str, int] = defaultdict(int)
        file_authors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        file_fixes: Dict[str, int] = defaultdict(int)

        for c in commits:
            for f in c.files_changed:
                if exclude_generated and is_auto_generated(f):
                    continue
                if exclude_infra and is_infra_only(f):
                    continue
                file_commits[f] += 1
                file_authors[f][c.author_name] += 1
                if c.is_fix:
                    file_fixes[f] += 1

        hotspots: List[FileHotspot] = []
        max_commits = max(file_commits.values()) if file_commits else 1

        for f, count in file_commits.items():
            author_map = file_authors[f]
            authors_count = len(author_map)
            fixes = file_fixes[f]

            top_author, top_author_commits = max(author_map.items(), key=lambda item: item[1]) if author_map else ("", 0)
            top_author_pct = round((top_author_commits / count) * 100, 1) if count else 0.0

            norm_commits = count / max_commits
            norm_fixes = min(fixes / 4.0, 1.0)
            norm_authors = min(authors_count / 5.0, 1.0)

            churn_raw = (norm_commits * 0.50) + (norm_fixes * 0.35) + (norm_authors * 0.15)
            churn_score = round(churn_raw * 100, 1)

            if churn_score >= 70.0:
                risk = "CRITICAL"
            elif churn_score >= 45.0:
                risk = "HIGH"
            elif churn_score >= 20.0:
                risk = "MEDIUM"
            else:
                risk = "LOW"

            hotspots.append(FileHotspot(
                file_path=f,
                commit_count=count,
                authors_count=authors_count,
                fix_count=fixes,
                top_author=top_author,
                top_author_percentage=top_author_pct,
                churn_score=churn_score,
                risk_level=risk
            ))

        hotspots.sort(key=lambda x: x.churn_score, reverse=True)
        return hotspots

    def detect_ghost_coupling(
        self,
        commits: List[CommitInfo],
        min_confidence: float = 0.5,
        exclude_generated: bool = True,
        exclude_infra: bool = True,
    ) -> List[CouplingPair]:
        """
        Detecta pares de archivos que cambian habitualmente juntos.
        Filtra automáticamente archivos generados/infra para reducir falsos positivos.
        Genera diagnósticos enriquecidos y accionables por patrón arquitectónico.
        """
        if not commits:
            return []

        pair_counts: Dict[Tuple[str, str], int] = defaultdict(int)
        file_counts: Dict[str, int] = defaultdict(int)

        for c in commits:
            files = [
                f for f in set(c.files_changed)
                if not (exclude_generated and is_auto_generated(f))
                and not (exclude_infra and is_infra_only(f))
            ]
            # Ignorar commits masivos (formateos o merges globales)
            if len(files) > 15 or len(files) < 2:
                continue

            for f in files:
                file_counts[f] += 1

            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    fa, fb = sorted([files[i], files[j]])
                    pair_counts[(fa, fb)] += 1

        couplings: List[CouplingPair] = []
        for (fa, fb), co_count in pair_counts.items():
            if co_count < 2:
                continue

            min_base = min(file_counts[fa], file_counts[fb])
            if min_base == 0:
                continue
            confidence = round(co_count / min_base, 2)

            if confidence >= min_confidence:
                insight = generate_coupling_insight(fa, fb, co_count, confidence)
                couplings.append(CouplingPair(
                    file_a=fa,
                    file_b=fb,
                    co_commit_count=co_count,
                    confidence=confidence,
                    explanation=insight
                ))

        couplings.sort(key=lambda x: (x.co_commit_count, x.confidence), reverse=True)
        return couplings

    def calculate_bus_factor(self, commits: List[CommitInfo]) -> List[AuthorBusFactor]:
        """Calcula la concentración de propiedad de código por autor (solo código fuente)."""
        if not commits:
            return []

        author_commits: Dict[str, int] = defaultdict(int)
        file_authors: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        total_commits = len(commits)

        for c in commits:
            author_commits[c.author_name] += 1
            for f in c.files_changed:
                if not is_auto_generated(f) and not is_infra_only(f):
                    file_authors[f][c.author_name] += 1

        owned_files: Dict[str, int] = defaultdict(int)
        for f, authors in file_authors.items():
            top_author = max(authors.items(), key=lambda i: i[1])[0]
            owned_files[top_author] += 1

        factors: List[AuthorBusFactor] = []
        for author, count in author_commits.items():
            factors.append(AuthorBusFactor(
                author_name=author,
                commit_count=count,
                files_owned_count=owned_files[author],
                ownership_percentage=round((count / total_commits) * 100, 1)
            ))

        factors.sort(key=lambda x: x.ownership_percentage, reverse=True)
        return factors

    def compare_branches_for_breaking_changes(self, base_branch: str = "main", target_branch: str = "develop") -> List[BreakingChangeInfo]:
        """Compara dos ramas y extrae cambios que rompen firmas de símbolos públicos."""
        breaking: List[BreakingChangeInfo] = []
        try:
            diff_files = self._run_git(["diff", "--name-only", f"{base_branch}...{target_branch}"])
            for f in diff_files.strip().split("\n"):
                f = f.strip()
                if not f or not Path(f).suffix in [".py", ".dart", ".ts", ".js", ".rs", ".go"]:
                    continue

                old_content = self._run_git(["show", f"{base_branch}:{f}"])
                new_content = self._run_git(["show", f"{target_branch}:{f}"])

                removed = ASTEngine.detect_removed_symbols(f, old_content, new_content)
                for sym in removed:
                    breaking.append(BreakingChangeInfo(
                        file_path=f,
                        change_type="REMOVED_SYMBOL",
                        symbol_name=sym,
                        description=f"El símbolo público '{sym}' fue eliminado o renombrado en la rama {target_branch}."
                    ))
        except Exception:
            pass
        return breaking
