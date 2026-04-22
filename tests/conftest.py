import sys
from pathlib import Path

# Make scripts/ importable as a module root.
SCRIPTS = Path(__file__).parent.parent / "b2-cloud-storage" / "scripts"
sys.path.insert(0, str(SCRIPTS))
