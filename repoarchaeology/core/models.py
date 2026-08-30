"""
Estructuras de datos y modelos del dominio forense.
"""
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Información extraída de un commit."""
    hash: str
    short_hash: str
    author_name: str
    author_email: str
    date: datetime
    message: str
    files_changed: List[str] = Field(default_factory=list)
    insertions: int = 0
    deletions: int = 0
    is_fix: bool = False


class FileHotspot(BaseModel):
    """Métrica de punto caliente (hotspot) para un archivo."""
    file_path: str
    commit_count: int
    authors_count: int
    fix_count: int
    lines_added: int
    lines_deleted: int
    churn_score: float
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW


class CouplingPair(BaseModel):
    """Par de archivos con acoplamiento fantasma (co-modificación)."""
    file_a: str
    file_b: str
    co_commit_count: int
    confidence: float  # De 0.0 a 1.0


class RepoHealthReport(BaseModel):
    """Diagnóstico general de salud del repositorio."""
    repo_name: str
    scan_date: datetime = Field(default_factory=datetime.utcnow)
    total_commits_analyzed: int
    total_files_analyzed: int
    health_score: int  # 0 a 100
    hotspots: List[FileHotspot] = Field(default_factory=list)
    ghost_couplings: List[CouplingPair] = Field(default_factory=list)
    bus_factor_risk: Dict[str, float] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
