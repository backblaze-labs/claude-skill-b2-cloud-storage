from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "b2-cloud-storage"
SKILL_MD = SKILL_DIR / "SKILL.md"
DOCS_WITH_INSTALL_GUIDANCE = [
    SKILL_MD,
    ROOT / "README.md",
    *sorted((SKILL_DIR / "references").glob("*.md")),
]

UNPINNED_B2_INSTALL = re.compile(r"\bpip3?\s+install\s+(?:--\S+\s+)*b2\b", re.IGNORECASE)


def test_skill_does_not_allow_package_install_tools() -> None:
    frontmatter = SKILL_MD.read_text(encoding="utf-8").split("---", 2)[1]
    allowed_tools = next(
        line for line in frontmatter.splitlines() if line.startswith("allowed-tools:")
    )

    assert "Bash(pip:" not in allowed_tools
    assert "Bash(pip3:" not in allowed_tools


def test_docs_do_not_instruct_unpinned_b2_install() -> None:
    unsafe_matches = {
        path.relative_to(ROOT).as_posix(): UNPINNED_B2_INSTALL.findall(
            path.read_text(encoding="utf-8")
        )
        for path in DOCS_WITH_INSTALL_GUIDANCE
    }

    assert unsafe_matches == {
        path.relative_to(ROOT).as_posix(): [] for path in DOCS_WITH_INSTALL_GUIDANCE
    }
