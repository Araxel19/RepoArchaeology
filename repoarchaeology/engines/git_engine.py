"""
Motor de minería y análisis forense de repositorios Git.
"""
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

from repoarchaeology.core.models import CommitInfo, FileHotspot, CouplingPair
from repoarchaeology.core.security import redact_secrets


class GitEngine:
    """Extractor y analizador de métricas forenses sobre Git."""
    
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self._validate_repo()
        
    def _validate_repo(self) -> None:
        if not (self.repo_path / ".git").exists():
            raise ValueError(f"El directorio '{self.repo_path}' no es un repositorio Git válido.")
            
    def _run_git(self, args: List[str]) -> str:
        """Ejecuta un comando git de forma segura con timeout."""
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
            raise RuntimeError(f"Error al ejecutar git: {result.stderr.strip()}")
        return result.stdout

    def extract_commits(self, max_count: int = 500) -> List[CommitInfo]:
        """Extrae el historial de commits estructurado con cambios por archivo."""
        format_str = "%H%x1f%h%x1f%an%x1f%ae%x1f%at%x1f%s"
        log_out = self._run_git([
            "log",
            f"-n{max_count}",
            f"--format={format_str}",
            "--name-only"
        ])
        
        commits: List[CommitInfo] = []
        entries = log_out.strip().split("\n\n")
        
        for entry in entries:
            if not entry.strip():
                continue
            lines = entry.strip().split("\n")
            header = lines[0].split("\x1f")
            if len(header) < 6:
                continue
                
            h, sh, author, email, ts, msg = header[0], header[1], header[2], header[3], header[4], header[5]
            files = [f.strip() for f in lines[1:] if f.strip()]
            
            # Detección simple de commits de corrección
            msg_clean = redact_secrets(msg)
            is_fix = any(w in msg_clean.lower() for w in ["fix", "bug", "hotfix", "patch", "error", "issue", "repair", "corrige"])
            
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
                is_fix=is_fix
            ))
            
        return commits

    def calculate_hotspots(self, commits: List[CommitInfo]) -> List[FileHotspot]:
        """Calcula la métrica de Code Churn y nivel de riesgo por archivo."""
        file_commits = defaultdict(int)
        file_authors = defaultdict(set)
        file_fixes = defaultdict(int)
        
        for c in commits:
            for f in c.files_changed:
                file_commits[f] += 1
                file_authors[f].add(c.author_name)
                if c.is_fix:
                    file_fixes[f] += 1
                    
        hotspots: List[FileHotspot] = []
        max_commits = max(file_commits.values()) if file_commits else 1
        
        for f, count in file_commits.items():
            authors_count = len(file_authors[f])
            fixes = file_fixes[f]
            
            # Score normalizado: frecuencia de cambio + peso por fixes repetidos
            churn_score = (count / max_commits) * 0.6 + min(fixes / 5.0, 1.0) * 0.4
            
            if churn_score >= 0.75:
                risk = "CRITICAL"
            elif churn_score >= 0.50:
                risk = "HIGH"
            elif churn_score >= 0.25:
                risk = "MEDIUM"
            else:
                risk = "LOW"
                
            hotspots.append(FileHotspot(
                file_path=f,
                commit_count=count,
                authors_count=authors_count,
                fix_count=fixes,
                lines_added=0,
                lines_deleted=0,
                churn_score=round(churn_score * 100, 1),
                risk_level=risk
            ))
            
        hotspots.sort(key=lambda x: x.churn_score, reverse=True)
        return hotspots

    def detect_ghost_coupling(self, commits: List[CommitInfo], min_confidence: float = 0.5) -> List[CouplingPair]:
        """Detecta pares de archivos que cambian habitualmente juntos."""
        pair_counts = defaultdict(int)
        file_counts = defaultdict(int)
        
        for c in commits:
            files = list(set(c.files_changed))
            # Ignorar commits masivos que suelen ser renames o formatedores
            if len(files) > 15:
                continue
                
            for f in files:
                file_counts[f] += 1
                
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    fa, fb = sorted([files[i], files[j]])
                    pair_counts[(fa, fb)] += 1
                    
        couplings: List[CouplingPair] = []
        for (fa, fb), co_count in pair_counts.items():
            if co_count < 3:
                continue
            # Confianza basada en índice de Jaccard / Co-ocurrencia
            confidence = co_count / min(file_counts[fa], file_counts[fb])
            if confidence >= min_confidence:
                couplings.append(CouplingPair(
                    file_a=fa,
                    file_b=fb,
                    co_commit_count=co_count,
                    confidence=round(confidence, 2)
                ))
                
        couplings.sort(key=lambda x: (x.co_commit_count, x.confidence), reverse=True)
        return couplings
