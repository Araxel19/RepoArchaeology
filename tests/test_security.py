import pytest
from pathlib import Path
from repoarchaeology.core.security import sanitize_path, redact_secrets


def test_redact_secrets():
    raw = "Fix crash when api_key='sk-1234567890abcdef12345678' is invalid"
    cleaned = redact_secrets(raw)
    assert "[REDACTED_SECRET]" in cleaned
    assert "sk-1234567890abcdef12345678" not in cleaned


def test_sanitize_path(tmp_path):
    safe_path = sanitize_path("src/module.py", base_dir=tmp_path)
    assert safe_path == (tmp_path / "src/module.py").resolve()
