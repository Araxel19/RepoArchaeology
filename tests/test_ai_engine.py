from datetime import datetime
from repoarchaeology.core.models import CommitInfo
from repoarchaeology.engines.ai_engine import AIEngine


def test_heuristic_lore_offline():
    engine = AIEngine(provider="offline")
    commits = [
        CommitInfo(
            hash="1234567890abcdef",
            short_hash="1234567",
            author_name="Araxel",
            author_email="araxel@example.com",
            date=datetime(2026, 1, 15),
            message="fix: resolve race condition in token refresh",
            files_changed=["auth_service.py"],
            is_fix=True
        ),
        CommitInfo(
            hash="abcdef1234567890",
            short_hash="abcdef1",
            author_name="Araxel",
            author_email="araxel@example.com",
            date=datetime(2025, 12, 1),
            message="feat: initial auth service implementation",
            files_changed=["auth_service.py"]
        )
    ]
    
    summary = engine.summarize_file_lore("auth_service.py", commits)
    assert "auth_service.py" in summary
    assert "Araxel" in summary
    assert "parches de corrección" in summary or "Diagnóstico de Estabilidad" in summary
