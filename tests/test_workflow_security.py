from __future__ import annotations

import re
from pathlib import Path

import yaml

WORKFLOW_DIR = Path(__file__).parent.parent / ".github" / "workflows"
PINNED_ACTION = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[a-f0-9]{40}$")


def _workflow_steps() -> list[tuple[Path, dict[str, object]]]:
    steps: list[tuple[Path, dict[str, object]]] = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for job in data.get("jobs", {}).values():
            for step in job.get("steps", []):
                steps.append((path, step))
    return steps


def test_workflow_actions_are_pinned_to_full_commit_shas() -> None:
    unpinned = []
    for path, step in _workflow_steps():
        uses = step.get("uses")
        if isinstance(uses, str) and not PINNED_ACTION.match(uses):
            unpinned.append(f"{path.name}: {uses}")

    assert unpinned == []


def test_checkout_does_not_persist_credentials() -> None:
    unsafe = []
    for path, step in _workflow_steps():
        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith("actions/checkout@"):
            with_config = step.get("with") or {}
            if (
                not isinstance(with_config, dict)
                or with_config.get("persist-credentials") is not False
            ):
                unsafe.append(path.name)

    assert unsafe == []
