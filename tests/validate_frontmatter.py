"""Validate SKILL.md frontmatter has the required fields.

Usage: python tests/validate_frontmatter.py <path-to-SKILL.md>
"""

import sys
from pathlib import Path

import yaml

REQUIRED = ["name", "description", "compatibility", "allowed-tools"]


def load_frontmatter(path):
    text = Path(path).read_text()
    if not text.startswith("---"):
        raise SystemExit(f"{path}: no frontmatter")
    _, fm, _ = text.split("---", 2)
    return yaml.safe_load(fm)


def main():
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
