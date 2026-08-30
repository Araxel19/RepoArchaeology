"""
Motor ligero de análisis sintáctico (AST y expresiones estructurales).
Permite detectar firmas públicas, clases y breaking changes sin dependencias pesadas.
"""
import re
import ast
from pathlib import Path
from typing import List, Set, Dict


class ASTEngine:
    """Parser estructural multi-lenguaje para extraer símbolos públicos."""

    @staticmethod
    def extract_symbols_from_python(source_code: str) -> Set[str]:
        """Extrae clases y funciones públicas de código Python."""
        symbols = set()
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        symbols.add(f"func:{node.name}")
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith("_"):
                        symbols.add(f"class:{node.name}")
        except Exception:
            pass
        return symbols

    @staticmethod
    def extract_symbols_generic(source_code: str, file_ext: str) -> Set[str]:
        """Extrae símbolos públicos para Dart, TypeScript, JS, Rust, Go via regex estructural."""
        symbols = set()
        
        # Dart / TS / JS / Java classes
        class_matches = re.findall(r'(?:export\s+)?class\s+([A-Za-z0-9_]+)', source_code)
        for c in class_matches:
            symbols.add(f"class:{c}")

        # Dart / TS / JS functions
        func_matches = re.findall(r'(?:export\s+)?(?:async\s+)?function\s+([A-Za-z0-9_]+)', source_code)
        for f in func_matches:
            symbols.add(f"func:{f}")
            
        # Rust functions / structs
        rust_matches = re.findall(r'pub\s+(?:fn|struct|enum|trait)\s+([A-Za-z0-9_]+)', source_code)
        for r in rust_matches:
            symbols.add(f"pub:{r}")

        return symbols

    @classmethod
    def extract_symbols(cls, file_path: str, content: str) -> Set[str]:
        """Enrutador de extracción según la extensión del archivo."""
        ext = Path(file_path).suffix.lower()
        if ext == ".py":
            py_symbols = cls.extract_symbols_from_python(content)
            if py_symbols:
                return py_symbols
        return cls.extract_symbols_generic(content, ext)

    @classmethod
    def detect_removed_symbols(cls, file_path: str, old_content: str, new_content: str) -> List[str]:
        """Compara dos versiones de un archivo y lista símbolos eliminados (breaking changes)."""
        old_symbols = cls.extract_symbols(file_path, old_content)
        new_symbols = cls.extract_symbols(file_path, new_content)
        removed = old_symbols - new_symbols
        return sorted(list(removed))
