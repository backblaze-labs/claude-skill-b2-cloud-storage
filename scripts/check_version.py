#!/usr/bin/env python3
"""Verify that a tag matches every version field in the repo.

Usage:
    scripts/check_version.py v1.2.0
    scripts/check_version.py 1.2.0      # leading 'v' optional

Exits 0 if every version field equals the given version, non-zero otherwise.

Checked fields:
    - .claude-plugin/marketplace.json    metadata.version
    - .claude-plugin/marketplace.json    plugins[].version  (every entry)
    - b2-cloud-storage/SKILL.md          frontmatter metadata.version

Used by .github/workflows/release.yml as the gate before building artifacts,
and by humans before running `git tag` if they want belt-and-suspenders.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
SKILL_MD = REPO / "b2-cloud-storage" / "SKILL.md"

SKILL_VERSION_RE = re.compile(r'^\s*version:\s*"([^"]+)"', re.MULTILINE)


def normalize(tag: str) -> str:
    return tag.removeprefix("v")


def collect_versions() -> dict[str, str]:
    """Return {label: version} for every place a version lives."""
    versions: dict[str, str] = {}

    data = json.loads(MARKETPLACE.read_text())
    versions["marketplace.json metadata.version"] = str(data["metadata"]["version"])
    for plugin in data.get("plugins", []):
        name = plugin.get("name", "<unnamed>")
        if "version" not in plugin:
            versions[f"marketplace.json plugins[{name}].version"] = "<missing>"
        else:
            versions[f"marketplace.json plugins[{name}].version"] = str(plugin["version"])

    text = SKILL_MD.read_text()
    m = SKILL_VERSION_RE.search(text)
    versions["SKILL.md metadata.version"] = m.group(1) if m else "<not found>"

    return versions


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    expected = normalize(sys.argv[1])
    versions = collect_versions()

    mismatches = {label: v for label, v in versions.items() if v != expected}

    width = max(len(label) for label in versions)
    print(f"Expected: {expected}")
    print()
    for label, v in versions.items():
        ok = "✓" if v == expected else "✗"
        print(f"  {ok}  {label:<{width}}  {v}")

    if mismatches:
        print()
        print(
            f"FAIL: {len(mismatches)} version field(s) do not match {expected!r}.", file=sys.stderr
        )
        return 1

    print()
    print(f"OK: all {len(versions)} version field(s) match {expected!r}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
