"""
Motor de análisis forense y minería de Git de alto rendimiento.
Incluye filtrado inteligente de archivos generados/automáticos, infraestructura y sincronizaciones naturales.
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
# Patrones de archivos auto-generados
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
    re.compile(r"(^|/)CHANGELOG\.md$", re.IGNORECASE),
    re.compile(r"(^|/)CHANGELOG\.rst$", re.IGNORECASE),

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

# Archivos de infraestructura, documentación y scripts de empaquetado
INFRA_PATTERNS: List[re.Pattern] = [
    re.compile(r"\.md$", re.IGNORECASE),
    re.compile(r"\.rst$", re.IGNORECASE),
    re.compile(r"\.txt$", re.IGNORECASE),
    re.compile(r"(^|/)LICENSE", re.IGNORECASE),
    re.compile(r"(^|/)\.gitignore$"),
    re.compile(r"(^|/)\.gitattributes$"),
    re.compile(r"(^|/)Makefile$"),
    re.compile(r"(^|/)Dockerfile$"),
    re.compile(r"(^|/)docker-compose\.ya?ml$"),
    re.compile(r"(^|/)\.env(\..+)?$"),
    re.compile(r"(^|/)\.github/"),
    re.compile(r"(^|/)\.gitlab-ci\.ya?ml$"),
    re.compile(r"(^|/)\.(travis|circleci|jenkins)\.ya?ml$"),
    re.compile(r"\.(iss|bat|cmd|ps1)$", re.IGNORECASE),
    re.compile(r"(^|/)installer/", re.IGNORECASE),
]

# Archivos de configuración de alto nivel (manifiestos de paquetes y dependencias)
HIGH_LEVEL_CONFIG_PATTERNS: List[re.Pattern] = [
    re.compile(r"(^|/)pubspec\.ya?ml$"),
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

# Etiquetas de rol compactas para evitar saltos de línea antiestéticos
ROLE_LABELS: Dict[str, str] = {
    ".dart":  "Dart",
    ".py":    "Python",
    ".js":    "JavaScript",
    ".jsx":   "React",
    ".ts":    "TypeScript",
    ".tsx":   "React TS",
    ".go":    "Go",
    ".rs":    "Rust",
    ".java":  "Java",
    ".kt":    "Kotlin",
    ".swift": "Swift",
    ".vue":   "Vue",
    ".svelte":"Svelte",
    ".yaml":  "Config YAML",
    ".yml":   "Config YAML",
    ".toml":  "Config TOML",
    ".json":  "JSON",
    ".arb":   "Localización",
    ".sql":   "SQL",
    ".sh":    "Shell Script",
    ".html":  "HTML",
    ".css":   "CSS",
    ".scss":  "SCSS",
}


def is_auto_generated(file_path: str) -> bool:
    """Detecta si un archivo es generado automáticamente."""
    for pattern in GENERATED_FILE_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def is_infra_only(file_path: str) -> bool:
    """Detecta si un archivo es solo infraestructura/documentación/script del repo."""
    for pattern in INFRA_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def is_high_level_config(file_path: str) -> bool:
    """Detecta si un archivo es configuración de manifiesto/dependencias."""
    for pattern in HIGH_LEVEL_CONFIG_PATTERNS:
        if pattern.search(file_path):
            return True
    return False


def is_l10n(file_path: str) -> bool:
    """Detecta si es un archivo de recursos de traducción/localización."""
    fp = file_path.lower()
    return Path(file_path).suffix.lower() in (".arb", ".po", ".strings") or "/l10n/" in fp or "/i18n/" in fp or "/locales/" in fp


def get_file_role(file_path: str) -> str:
    """Devuelve un rol semántico compacto para el archivo."""
    if is_high_level_config(file_path):
        return "Configuración"
    if is_l10n(file_path):
        return "Localización"
    suffix = Path(file_path).suffix.lower()
    return ROLE_LABELS.get(suffix, suffix[1:].upper() if suffix else "Código")


def generate_coupling_insight(fa: str, fb: str, co_count: int, confidence: float) -> str:
    """
    Genera un diagnóstico enriquecido y accionable para el acoplamiento detectado.
    Evalúa el patrón arquitectónico subyacente entre archivos de código fuente.
    """
    ext_a = Path(fa).suffix.lower()
    ext_b = Path(fb).suffix.lower()
    dir_a = str(Path(fa).parent)
    dir_b = str(Path(fb).parent)

    # Detección semántica por arquitectura en capas
    if ("model" in fa.lower() or "domain" in fa.lower()) and ("repo" in fb.lower() or "data" in fb.lower()):
        return "Dependencia modelo→repositorio. Evalúa si el dominio filtra lógica de persistencia."
    if ("model" in fb.lower() or "domain" in fb.lower()) and ("repo" in fa.lower() or "data" in fa.lower()):
        return "Dependencia modelo→repositorio. Evalúa si el dominio filtra lógica de persistencia."

    if ("presenter" in fa.lower() or "viewmodel" in fa.lower() or "bloc" in fa.lower() or "cubit" in fa.lower()) and ("page" in fb.lower() or "screen" in fb.lower() or "view" in fb.lower()):
        return "Presenter/Bloc fuertemente ligado a su vista. Verifica separación clara de estado y UI."
    if ("presenter" in fb.lower() or "viewmodel" in fb.lower() or "bloc" in fb.lower() or "cubit" in fb.lower()) and ("page" in fa.lower() or "screen" in fa.lower() or "view" in fa.lower()):
        return "Presenter/Bloc fuertemente ligado a su vista. Verifica separación clara de estado y UI."

    if "controller" in fa.lower() and "route" in fb.lower():
        return "Controlador y rutas cambian juntos. Considera separar la definición de rutas del controlador."
    if "controller" in fb.lower() and "route" in fa.lower():
        return "Controlador y rutas cambian juntos. Considera separar la definición de rutas del controlador."

    if "service" in fa.lower() and "model" in fb.lower():
        return "Servicio vinculado a modelo. Si es frecuente, evalúa un UseCase o DTO intermedio."
    if "service" in fb.lower() and "model" in fa.lower():
        return "Servicio vinculado a modelo. Si es frecuente, evalúa un UseCase o DTO intermedio."

    if "test" in fa.lower() or "test" in fb.lower() or "_test." in fa or "_test." in fb:
        return "Test sincronizado con su módulo. Normal; asegura que cubre los casos límites del cambio."

    # Capas arquitectónicas Clean / Hexagonal
    layers_a = set(dir_a.lower().split("/"))
    layers_b = set(dir_b.lower().split("/"))
    cross_layer_markers = {"data", "domain", "presentation", "service", "ui", "routes", "api", "models"}
    a_layer = layers_a & cross_layer_markers
    b_layer = layers_b & cross_layer_markers

    if a_layer and b_layer and a_layer != b_layer:
        la = next(iter(a_layer))
        lb = next(iter(b_layer))
        return f"Acoplamiento entre capas '{la}' y '{lb}'. Verifica que se respetan las reglas de dependencia."

    if dir_a == dir_b:
        return "Co-modificación en la misma feature o carpeta. Evalúa si comparten demasiada lógica interna."

    if ext_a != ext_b:
        return f"Acoplamiento entre tecnologías ({ext_a} ↔ {ext_b}). Podría indicar falta de abstracción."

    return "Co-modificación recurrente. Evalúa extraer lógica compartida o documentar la dependencia."


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
        exclude_config: bool = True,
        exclude_l10n: bool = True,
    ) -> List[FileHotspot]:
        """
        Calcula la métrica de Code Churn ponderada con fix rate y autor principal.
        Filtra automáticamente archivos generados, infraestructura, manifiestos de configuración
        y archivos de traducción para centrarse exclusivamente en código fuente real.
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
                if exclude_config and is_high_level_config(f):
                    continue
                if exclude_l10n and is_l10n(f):
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
        exclude_config_pairs: bool = True,
        exclude_l10n_sync: bool = True,
    ) -> List[CouplingPair]:
        """
        Detecta pares de archivos que cambian habitualmente juntos (acoplamiento fantasma).
        Excluye pares espurios (manifiestos de paquetes con código, sincronización de traducciones i18n).
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

                    # Filtrar pares manifiesto de dependencias ↔ código fuente
                    if exclude_config_pairs and (is_high_level_config(fa) or is_high_level_config(fb)):
                        continue

                    # Filtrar sincronización natural de traducciones (ej: app_es.arb ↔ app_en.arb)
                    if exclude_l10n_sync and is_l10n(fa) and is_l10n(fb):
                        continue

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

    def calculate_health_score(
        self,
        commits: List[CommitInfo],
        hotspots: List[FileHotspot],
        couplings: List[CouplingPair],
        bus_factors: List[AuthorBusFactor],
    ) -> int:
        """
        Calcula un puntaje de salud calibrado proporcional al tamaño del repositorio.
        Puntaje sobre 100 basado en densidad de puntos críticos, acoplamiento real,
        tasa de fixes y concentración de equipo.
        """
        if not commits or not hotspots:
            return 100

        total_files = len(hotspots)
        critical_count = sum(1 for h in hotspots if h.risk_level == "CRITICAL")
        high_count = sum(1 for h in hotspots if h.risk_level == "HIGH")

        # 1. Densidad de Hotspots (Máx 35 pts de penalización)
        crit_density = critical_count / total_files
        high_density = high_count / total_files
        hotspot_penalty = (crit_density * 180.0) + (high_density * 60.0)
        hotspot_penalty = min(hotspot_penalty, 35.0)

        # 2. Densidad de Acoplamientos Fantasma Reales (Máx 30 pts de penalización)
        crit_couplings = sum(1 for c in couplings if c.confidence >= 0.8)
        norm_coupling_factor = (len(couplings) * 0.4 + crit_couplings * 1.6) / max(total_files * 0.08, 3.0)
        coupling_penalty = min(norm_coupling_factor * 10.0, 30.0)

        # 3. Presión de Bugs / Fix Rate (Máx 20 pts de penalización)
        total_fixes = sum(1 for c in commits if c.is_fix)
        fix_ratio = total_fixes / max(len(commits), 1)
        fix_penalty = min(fix_ratio * 35.0, 20.0)

        # 4. Bus Factor (Máx 15 pts) - Solo penaliza si es un equipo multi-autor (>2 desarrolladores)
        bus_penalty = 0.0
        if len(bus_factors) > 2 and bus_factors[0].ownership_percentage > 70.0:
            excess = bus_factors[0].ownership_percentage - 70.0
            bus_penalty = min(excess * 0.5, 15.0)

        raw_score = 100.0 - hotspot_penalty - coupling_penalty - fix_penalty - bus_penalty
        return max(min(int(round(raw_score)), 100), 20)

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
