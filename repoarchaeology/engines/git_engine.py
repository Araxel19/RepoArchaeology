"""
Motor de análisis forense y minería de Git de alto rendimiento.
"""
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Set
from collections import defaultdict

from repoarchaeology.core.models import CommitInfo, FileHotspot, CouplingPair, AuthorBusFactor, BreakingChangeInfo
from repoarchaeology.core.security import redact_secrets
from repoarchaeology.engines.ast_engine import ASTEngine


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

    def calculate_hotspots(self, commits: List[CommitInfo]) -> List[FileHotspot]:
        """Calcula la métrica de Code Churn ponderada con fix rate y autor principal."""
        if not commits:
            return []

        file_commits = defaultdict(int)
        file_authors = defaultdict(lambda: defaultdict(int))
        file_fixes = defaultdict(int)
        
        for c in commits:
            for f in c.files_changed:
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
            
            # Churn Score: Frecuencia de cambio (50%) + Peso por fixes (35%) + Fragmentación de autores (15%)
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

    def detect_ghost_coupling(self, commits: List[CommitInfo], min_confidence: float = 0.5) -> List[CouplingPair]:
        """Detecta pares de archivos que cambian habitualmente juntos (co-modificación invisible)."""
        if not commits:
            return []

        pair_counts = defaultdict(int)
        file_counts = defaultdict(int)
        
        for c in commits:
            files = list(set(c.files_changed))
            # Ignorar commits masivos (formateos o merges globales)
            if len(files) > 12 or len(files) < 2:
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
            confidence = round(co_count / min_base, 2)
            
            if confidence >= min_confidence:
                ext_a = Path(fa).suffix
                ext_b = Path(fb).suffix
                
                if ext_a != ext_b:
                    exp = f"Acoplamiento entre capas distintas ({ext_a} ↔ {ext_b})."
                else:
                    exp = "Co-modificación recurrente en la misma capa."
                    
                couplings.append(CouplingPair(
                    file_a=fa,
                    file_b=fb,
                    co_commit_count=co_count,
                    confidence=confidence,
                    explanation=exp
                ))
                
        couplings.sort(key=lambda x: (x.co_commit_count, x.confidence), reverse=True)
        return couplings

    def calculate_bus_factor(self, commits: List[CommitInfo]) -> List[AuthorBusFactor]:
        """Calcula la concentración de propiedad de código por autor."""
        if not commits:
            return []

        author_commits = defaultdict(int)
        file_authors = defaultdict(lambda: defaultdict(int))
        total_commits = len(commits)
        
        for c in commits:
            author_commits[c.author_name] += 1
            for f in c.files_changed:
                file_authors[f][c.author_name] += 1
                
        owned_files = defaultdict(int)
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
