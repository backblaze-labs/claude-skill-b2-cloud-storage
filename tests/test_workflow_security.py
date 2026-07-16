from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

WORKFLOW_DIR = Path(__file__).parent.parent / ".github" / "workflows"
# Fully pinned `uses`: owner/repo@<40-char sha> or owner/repo/sub/path@<40-char sha>.
PINNED_ACTION = re.compile(
    r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*@[a-f0-9]{40}$",
    re.IGNORECASE,
)
# First-party namespaces trusted in write-token jobs (e.g. actions/*, github/codeql-action).
TRUSTED_ACTION_PREFIXES = ("actions/", "github/")


def _workflow_docs() -> list[tuple[Path, dict[str, Any]]]:
    docs: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(WORKFLOW_DIR.glob("*.yml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{path.name} must contain a mapping document"
        docs.append((path, data))
    return docs


def _workflow_steps() -> list[tuple[Path, dict[str, Any]]]:
    steps: list[tuple[Path, dict[str, Any]]] = []
    for path, data in _workflow_docs():
        for job in data.get("jobs", {}).values():
            for step in job.get("steps", []):
                steps.append((path, step))
    return steps


def _contents_permission(permissions: object) -> object:
    if isinstance(permissions, dict):
        return permissions.get("contents")
    return permissions


def test_workflow_actions_are_pinned_to_full_commit_shas() -> None:
    unpinned = []
    for path, step in _workflow_steps():
        uses = step.get("uses")
        if isinstance(uses, str) and not PINNED_ACTION.match(uses):
            unpinned.append(
                f"{path.name}: {uses} "
                "(pin to the full 40-character commit SHA, e.g. owner/repo@<sha>)"
            )

    assert unpinned == []


def test_pinned_action_allows_subdirectory_actions() -> None:
    assert PINNED_ACTION.match(f"github/codeql-action/init@{'a' * 40}") is not None


def test_pinned_action_allows_uppercase_shas() -> None:
    assert PINNED_ACTION.match(f"actions/checkout@{'A' * 40}") is not None


def test_checkout_does_not_persist_credentials() -> None:
    unsafe = []
    for path, step in _workflow_steps():
        uses = step.get("uses")
        if isinstance(uses, str) and uses.startswith("actions/checkout@"):
            with_config = step.get("with") or {}
            # Must be explicitly False; a missing/None persist-credentials is unsafe.
            if (
                not isinstance(with_config, dict)
                or with_config.get("persist-credentials") is not False
            ):
                unsafe.append(path.name)

    assert unsafe == []


def test_non_release_workflows_are_explicitly_read_only() -> None:
    unsafe = []
    for path, data in _workflow_docs():
        if path.name == "release.yml":
            continue
        if _contents_permission(data.get("permissions")) != "read":
            unsafe.append(path.name)

    assert unsafe == []


def test_write_token_jobs_only_use_trusted_actions() -> None:
    unsafe = []
    for path, data in _workflow_docs():
        workflow_permissions = data.get("permissions")
        for job_name, job in data.get("jobs", {}).items():
            permissions = job.get("permissions", workflow_permissions)
            if _contents_permission(permissions) != "write":
                continue
            for step in job.get("steps", []):
                uses = step.get("uses")
                if isinstance(uses, str) and not uses.startswith(TRUSTED_ACTION_PREFIXES):
                    unsafe.append(f"{path.name}:{job_name}:{uses}")

    assert unsafe == []
