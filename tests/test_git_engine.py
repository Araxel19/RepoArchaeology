import pytest
from pathlib import Path
from repoarchaeology.engines.git_engine import GitEngine


def test_invalid_git_repo(tmp_path):
    with pytest.raises(ValueError):
        GitEngine(tmp_path)
