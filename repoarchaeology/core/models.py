"""
Modelos de datos para el dominio de arqueología de código.
"""
from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class CommitInfo(BaseModel):
    """Información estructurada de un commit."""
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
    is_refactor: bool = False
    is_breaking: bool = False


class FileHotspot(BaseModel):
    """Métrica de punto caliente (churn vs estabilidad) para un archivo."""
    file_path: str
    commit_count: int
    authors_count: int
    fix_count: int
    top_author: str = ""
    top_author_percentage: float = 0.0
    churn_score: float
    risk_level: str  # CRITICAL, HIGH, MEDIUM, LOW


class CouplingPair(BaseModel):
    """Acoplamiento fantasma entre dos archivos en el historial."""
    file_a: str
    file_b: str
    co_commit_count: int
    confidence: float
    explanation: str = ""


class AuthorBusFactor(BaseModel):
    """Métricas de concentración de autoría y factor de autobús."""
    author_name: str
    commit_count: int
    files_owned_count: int
    ownership_percentage: float


class BreakingChangeInfo(BaseModel):
    """Registro de cambio disruptivo detectado entre ramas o versiones."""
    file_path: str
    change_type: str  # REMOVED_SYMBOL, MODIFIED_SIGNATURE, DELETED_MODULE
    symbol_name: str
    description: str


class RepoHealthReport(BaseModel):
    """Informe completo del estado y salud del repositorio."""
    repo_name: str
    scan_date: datetime = Field(default_factory=datetime.utcnow)
    total_commits_analyzed: int
    total_files_analyzed: int
    health_score: int  # 0 a 100
    bus_factor_score: int  # 0 a 100
    hotspots: List[FileHotspot] = Field(default_factory=list)
    ghost_couplings: List[CouplingPair] = Field(default_factory=list)
    top_authors: List[AuthorBusFactor] = Field(default_factory=list)
    breaking_changes: List[BreakingChangeInfo] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
