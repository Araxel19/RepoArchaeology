import pytest
from repoarchaeology.engines.ast_engine import ASTEngine


def test_python_symbol_extraction():
    code = """
class UserService:
    def get_user(self, user_id):
        pass
        
    def _internal_helper(self):
        pass

def calculate_gpa():
    pass
"""
    symbols = ASTEngine.extract_symbols_from_python(code)
    assert "class:UserService" in symbols
    assert "func:get_user" in symbols
    assert "func:calculate_gpa" in symbols
    assert "func:_internal_helper" not in symbols


def test_removed_symbols_detection():
    old_code = """
class AuthService:
    def login(self): pass
    def old_deprecated_method(self): pass
"""
    new_code = """
class AuthService:
    def login(self): pass
"""
    removed = ASTEngine.detect_removed_symbols("service.py", old_code, new_code)
    assert "func:old_deprecated_method" in removed
