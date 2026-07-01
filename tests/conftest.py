import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Make scripts/ importable as a module root.
SCRIPTS = ROOT / "skills" / "b2-cloud-storage" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SCRIPTS))
