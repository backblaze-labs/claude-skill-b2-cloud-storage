import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Make repo release tooling and both skill + maintenance scripts importable in tests.
SKILL_SCRIPTS = ROOT / "skills" / "b2-cloud-storage" / "scripts"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(SKILL_SCRIPTS))
