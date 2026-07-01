from __future__ import annotations

import tarfile
import zipfile
from pathlib import Path

import pytest

import scripts.build_artifacts as build_artifacts


def archive_names(path: Path) -> set[str]:
    if path.name.endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            return set(zf.namelist())

    with tarfile.open(path, "r:gz") as tf:
        return set(tf.getnames())


def test_release_artifacts_use_public_archive_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(build_artifacts, "DIST", tmp_path)

    outputs = build_artifacts.build("v9.9.9")

    assert {path.name for path in outputs} == {
        "b2-cloud-storage-v9.9.9.tar.gz",
        "b2-cloud-storage-v9.9.9.zip",
        "b2-cloud-storage.tar.gz",
        "b2-cloud-storage.zip",
    }

    for archive in outputs:
        names = archive_names(archive)
        assert "b2-cloud-storage/SKILL.md" in names
        assert not any(name.startswith("skills/") for name in names)
        assert [
            name
            for name in names
            if name != "b2-cloud-storage" and not name.startswith("b2-cloud-storage/")
        ] == []
