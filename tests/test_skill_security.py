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

PIP_VALUE_OPTION = (
    r"(?:--(?:index-url|extra-index-url|find-links|trusted-host|proxy|cert|client-cert|"
    r"cache-dir|src|constraint|requirement|config-settings|global-option|install-option)"
    r"|-[ic])(?:=|\s+)\S+"
)
PIP_FLAG_OPTION = r"(?:--[A-Za-z0-9][\w-]*|-[A-Za-z])"
PIP_OPTIONS = rf"(?:(?:{PIP_VALUE_OPTION}|{PIP_FLAG_OPTION})\s+)*"
UNPINNED_B2_INSTALL = re.compile(
    r"\b(?:python3?\s+-m\s+)?pip3?\s+install\s+"
    + PIP_OPTIONS
    + r"b2(?:\[[^\]\s]+\])?(?=$|[\s`'\"),.;:\]}!?])",
    re.IGNORECASE,
)


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


def test_unpinned_b2_install_pattern_allows_pinned_package_specs() -> None:
    assert UNPINNED_B2_INSTALL.search("pip install b2")
    assert UNPINNED_B2_INSTALL.search("pip3 install --user b2")
    assert UNPINNED_B2_INSTALL.search("python -m pip install b2")
    assert UNPINNED_B2_INSTALL.search("`pip install b2`")
    assert UNPINNED_B2_INSTALL.search("Install with pip install b2, then verify")
    assert UNPINNED_B2_INSTALL.search("pip install b2.")
    assert UNPINNED_B2_INSTALL.search("pip install b2[crt]")
    assert UNPINNED_B2_INSTALL.search("pip install --index-url https://example.test/simple b2")
    assert UNPINNED_B2_INSTALL.search("pip install --index-url=https://example.test/simple b2")
    assert UNPINNED_B2_INSTALL.search("pip install -i https://example.test/simple b2")
    assert UNPINNED_B2_INSTALL.search(
        "pip install --extra-index-url https://example.test/simple --trusted-host example.test b2"
    )
    assert not UNPINNED_B2_INSTALL.search("pip install b2==4.0.0 --hash=sha256:abc")
    assert not UNPINNED_B2_INSTALL.search("pip install b2[crt]==4.0.0 --hash=sha256:abc")
    assert not UNPINNED_B2_INSTALL.search(
        "pip install --index-url https://example.test/simple b2==4.0.0"
    )
    assert not UNPINNED_B2_INSTALL.search("pip install b2~=4.0")
    assert not UNPINNED_B2_INSTALL.search("pip install b2>=4")
