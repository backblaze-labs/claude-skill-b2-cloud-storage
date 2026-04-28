#!/usr/bin/env python3
"""Bump version, rotate CHANGELOG, commit, and tag — like `npm version`.

Usage:
    scripts/release.py patch        # 1.1.0  -> 1.1.1
    scripts/release.py minor        # 1.1.0  -> 1.2.0
    scripts/release.py major        # 1.1.0  -> 2.0.0
    scripts/release.py 2.0.0        # explicit version

Optional flags:
    --dry-run        Print what would change; do not modify or commit.
    --no-tag         Bump + commit, but do not create the tag.
    --no-commit      Bump files only; leave for manual commit.
    --no-changelog   Skip CHANGELOG.md rotation.
    --allow-dirty    Skip the clean-tree check.
    --allow-any-branch  Skip the main/master branch check.

Updates version in:
  - b2-cloud-storage/SKILL.md  (frontmatter `metadata.version`)
  - .claude-plugin/marketplace.json  (`metadata.version` and every `plugins[].version`)

Rotates CHANGELOG.md:
  - Moves the body of `## [Unreleased]` into a new `## [X.Y.Z] - YYYY-MM-DD` section.
  - Empties the `## [Unreleased]` section so future work has a home.
  - Updates the link references at the bottom (compare URLs).

Then runs `git add ...`, `git commit -m "chore: release vX.Y.Z"`, and
`git tag -a vX.Y.Z -m "Release vX.Y.Z"`.

Does NOT push. Push manually with `git push --follow-tags`.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_MD = REPO / "b2-cloud-storage" / "SKILL.md"
MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"
CHANGELOG = REPO / "CHANGELOG.md"

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
# Matches the frontmatter `  version: "X.Y.Z"` line under `metadata:`.
SKILL_VERSION_RE = re.compile(r'^(\s*version:\s*)"[^"]*"', re.MULTILINE)
# Heading that opens the floating "Unreleased" section.
UNRELEASED_HEADING_RE = re.compile(r"^## \[Unreleased\][^\n]*\n", re.MULTILINE)
# Next versioned section (or the link-reference block); marks where Unreleased's body ends.
NEXT_SECTION_RE = re.compile(r"^(?:## \[|\[Unreleased\]:)", re.MULTILINE)
# Existing `[Unreleased]: <prefix>compare/v<old>...HEAD` link reference.
UNRELEASED_LINK_RE = re.compile(
    r"^(\[Unreleased\]:\s*)(.+?compare/)v[\d.]+(\.\.\.HEAD)\s*$",
    re.MULTILINE,
)


def read_current_version() -> str:
    """marketplace.json is the canonical source."""
    data = json.loads(MARKETPLACE.read_text())
    return str(data["metadata"]["version"])


def parse_bump(current: str, kind: str) -> str:
    if SEMVER_RE.match(kind):
        return kind
    m = SEMVER_RE.match(current)
    if not m:
        raise SystemExit(f"Current version {current!r} is not semver X.Y.Z")
    major, minor, patch = (int(p) for p in m.groups())
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    if kind == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise SystemExit(f"Unknown bump kind: {kind!r}. Use major/minor/patch or X.Y.Z")


def update_skill_md(new_version: str) -> None:
    text = SKILL_MD.read_text()
    new_text, n = SKILL_VERSION_RE.subn(rf'\g<1>"{new_version}"', text, count=1)
    if n != 1:
        raise SystemExit(f'Could not find `version: "..."` line in {SKILL_MD}')
    SKILL_MD.write_text(new_text)


def update_marketplace_json(new_version: str) -> None:
    data = json.loads(MARKETPLACE.read_text())
    data.setdefault("metadata", {})["version"] = new_version
    for plugin in data.get("plugins", []):
        plugin["version"] = new_version
    MARKETPLACE.write_text(json.dumps(data, indent=2) + "\n")


def rotate_changelog(new_version: str, previous_version: str) -> bool:
    """Move `## [Unreleased]` body to a new `## [X.Y.Z] - YYYY-MM-DD` section.

    Also updates the link references at the bottom (`[Unreleased]: ...HEAD` →
    points at the new version, and inserts a `[X.Y.Z]: ...compare/v<prev>...v<new>` line).

    Returns True if CHANGELOG.md was modified, False otherwise.
    """
    if not CHANGELOG.exists():
        print("  CHANGELOG.md not found; skipping rotation.")
        return False

    text = CHANGELOG.read_text()

    heading = UNRELEASED_HEADING_RE.search(text)
    if not heading:
        print("  No `## [Unreleased]` heading in CHANGELOG.md; skipping rotation.")
        return False

    body_start = heading.end()
    next_section = NEXT_SECTION_RE.search(text, pos=body_start)
    body_end = next_section.start() if next_section else len(text)

    body = text[body_start:body_end].strip("\n")
    if not body:
        print("  [Unreleased] section is empty; nothing to rotate.")
        return False

    today = date.today().isoformat()
    new_section = f"## [{new_version}] - {today}\n\n{body}\n\n"

    rebuilt = text[:body_start] + "\n" + new_section + text[body_end:].lstrip("\n")

    rebuilt = _update_changelog_links(rebuilt, new_version, previous_version)

    CHANGELOG.write_text(rebuilt)
    print(f"  Rotated  CHANGELOG.md  ([Unreleased] → [{new_version}] - {today})")
    return True


def _update_changelog_links(text: str, new_version: str, previous_version: str) -> str:
    """Repoint `[Unreleased]:` at the new version and insert a `[X.Y.Z]:` line below."""
    m = UNRELEASED_LINK_RE.search(text)
    if not m:
        return text

    label_prefix, compare_prefix, head_suffix = m.group(1), m.group(2), m.group(3)
    new_unreleased = f"{label_prefix}{compare_prefix}v{new_version}{head_suffix}"
    new_version_ref = f"[{new_version}]: {compare_prefix}v{previous_version}...v{new_version}"

    return UNRELEASED_LINK_RE.sub(f"{new_unreleased}\n{new_version_ref}", text, count=1)


def run(cmd: list[str]) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout.strip()


def ensure_clean_tree() -> None:
    if run(["git", "status", "--porcelain"]):
        raise SystemExit("Working tree is not clean. Commit or stash first.")


def ensure_on_default_branch() -> None:
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    if branch not in ("main", "master"):
        raise SystemExit(f"Refusing to release from branch {branch!r}; use main/master.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("kind", help="major | minor | patch | X.Y.Z")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-tag", action="store_true", help="Skip creating the git tag")
    parser.add_argument(
        "--no-commit", action="store_true", help="Update files only; no git operations"
    )
    parser.add_argument("--allow-dirty", action="store_true", help="Allow uncommitted changes")
    parser.add_argument("--allow-any-branch", action="store_true", help="Allow non-default branch")
    parser.add_argument("--no-changelog", action="store_true", help="Skip CHANGELOG.md rotation")
    args = parser.parse_args()

    if not args.dry_run and not args.no_commit:
        if not args.allow_dirty:
            ensure_clean_tree()
        if not args.allow_any_branch:
            ensure_on_default_branch()

    current = read_current_version()
    new_version = parse_bump(current, args.kind)

    if new_version == current:
        raise SystemExit(f"New version {new_version} matches current; nothing to do.")

    print(f"Bumping {current}  ->  {new_version}")

    if args.dry_run:
        print("DRY RUN — no files modified, no git operations.")
        return

    update_skill_md(new_version)
    update_marketplace_json(new_version)
    print(f"  Updated  {SKILL_MD.relative_to(REPO)}")
    print(f"  Updated  {MARKETPLACE.relative_to(REPO)}")

    files_to_stage: list[Path] = [SKILL_MD, MARKETPLACE]
    if not args.no_changelog and rotate_changelog(new_version, current):
        files_to_stage.append(CHANGELOG)

    if args.no_commit:
        print("\nFiles updated. Run `git add` + `git commit` + `git tag` yourself.")
        return

    tag = f"v{new_version}"
    run(["git", "add", *[str(p) for p in files_to_stage]])
    run(["git", "commit", "-m", f"chore: release {tag}"])
    print(f"  Committed: chore: release {tag}")

    if args.no_tag:
        print(f"\nCommitted but not tagged. Tag with:  git tag -a {tag} -m 'Release {tag}'")
        return

    run(["git", "tag", "-a", tag, "-m", f"Release {tag}"])
    print(f"  Tagged:    {tag}")
    print("\n✓ Done. Push with:  git push --follow-tags")


if __name__ == "__main__":
    main()
