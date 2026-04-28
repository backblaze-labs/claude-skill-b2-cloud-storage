#!/usr/bin/env python3
"""Build release artifacts: .tar.gz + .zip of the skill directory.

Usage:
    scripts/build_artifacts.py v1.2.0
    scripts/build_artifacts.py 1.2.0      # leading 'v' optional

Outputs into dist/:
    b2-cloud-storage-<tag>.tar.gz
    b2-cloud-storage-<tag>.zip

Both archives root at `b2-cloud-storage/` so a consumer can extract directly
into `~/.claude/skills/`.

Used by .github/workflows/release.yml on tag push, and works locally too:
    python scripts/build_artifacts.py v1.2.0 && ls -la dist/
"""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / "b2-cloud-storage"
DIST = REPO / "dist"

# Patterns to keep out of release artifacts. These are dev-time noise that
# should never ship to skill consumers.
EXCLUDED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}


def normalize_tag(arg: str) -> str:
    return arg if arg.startswith("v") else f"v{arg}"


def is_excluded(path: Path) -> bool:
    if path.suffix in EXCLUDED_SUFFIXES:
        return True
    return any(part in EXCLUDED_DIR_NAMES for part in path.parts)


def build(tag: str) -> list[Path]:
    """Build versioned and unversioned tar.gz/zip pairs.

    The unversioned aliases (`b2-cloud-storage.tar.gz`, `b2-cloud-storage.zip`)
    let consumers use a stable URL: `releases/latest/download/b2-cloud-storage.tar.gz`.
    The versioned copies (`b2-cloud-storage-<tag>.{tar.gz,zip}`) preserve the
    version in the filename for archival or pinned downloads.
    """
    if not SKILL_DIR.is_dir():
        raise SystemExit(f"Skill directory not found: {SKILL_DIR}")

    DIST.mkdir(exist_ok=True)

    def tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        return None if is_excluded(Path(info.name)) else info

    outputs: list[Path] = []
    for stem in (f"b2-cloud-storage-{tag}", "b2-cloud-storage"):
        tarball = DIST / f"{stem}.tar.gz"
        with tarfile.open(tarball, "w:gz") as tf:
            tf.add(SKILL_DIR, arcname="b2-cloud-storage", filter=tar_filter)
        outputs.append(tarball)

        archive = DIST / f"{stem}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(SKILL_DIR.rglob("*")):
                if path.is_file() and not is_excluded(path):
                    zf.write(path, path.relative_to(REPO))
        outputs.append(archive)

    return outputs


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2

    tag = normalize_tag(sys.argv[1])
    outputs = build(tag)

    print(f"Built artifacts in {DIST.relative_to(REPO)}/:")
    for p in outputs:
        size_mb = p.stat().st_size / 1024 / 1024
        print(f"  {p.name:50s}  {size_mb:6.2f} MB")

    versioned_tarball = next(p for p in outputs if p.name.endswith(f"-{tag}.tar.gz"))
    print("\nContents:")
    with tarfile.open(versioned_tarball, "r:gz") as tf:
        for member in tf.getmembers():
            kind = "d" if member.isdir() else "f"
            print(f"  [{kind}] {member.name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
