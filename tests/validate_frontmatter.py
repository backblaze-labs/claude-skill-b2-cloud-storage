"""Validate SKILL.md frontmatter has the required fields.

Usage: python tests/validate_frontmatter.py <path-to-SKILL.md>
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REQUIRED: list[str] = ["name", "description", "compatibility", "allowed-tools"]


def load_frontmatter(path: str) -> dict[str, Any]:
    text = Path(path).read_text()
    if not text.startswith("---"):
        raise SystemExit(f"{path}: no frontmatter")
    closing = text.find("---", 3)
    if closing == -1:
        raise SystemExit(f"{path}: missing closing frontmatter delimiter")
    fm = text[3:closing]
    parsed = yaml.safe_load(fm)
    if not isinstance(parsed, dict):
        raise SystemExit(f"{path}: frontmatter is not a mapping")
    return parsed


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: validate_frontmatter.py <SKILL.md>")
    fm = load_frontmatter(sys.argv[1])
    missing = [k for k in REQUIRED if k not in fm]
    if missing:
        raise SystemExit(f"Missing required frontmatter fields: {missing}")
    # allowed-tools must be a string
    if not isinstance(fm["allowed-tools"], str):
        raise SystemExit("allowed-tools must be a string")
    # description should be specific enough to guide invocation
    if len(fm["description"]) < 40:
        raise SystemExit("description is too short to be useful for invocation")
    print(f"{sys.argv[1]}: frontmatter OK")


if __name__ == "__main__":
    main()
