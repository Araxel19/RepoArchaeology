"""
Punto de entrada para ejecución directa vía 'python -m repoarchaeology'.
"""
import sys
from repoarchaeology.cli.entrypoint import main

if __name__ == "__main__":
    sys.exit(main())
