"""conftest.py — ajoute la racine du projet à sys.path pour pytest."""

import sys
from pathlib import Path

# Assure que le répertoire racine est en premier dans sys.path
root = Path(__file__).parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
