"""Tests for storage_audit.py.

The B2 CLI is mocked by patching `storage_audit.run_b2`.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
import storage_audit as sa

NOW_MS = 1_700_000_000_000  # fixed "now" for stable age calcs — actual `now` comes from datetime


def _ts(days_ago: int) -> int:
    """Milliseconds timestamp N days before now-ish."""
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    return int((now - timedelta(days=days_ago)).timestamp() * 1000)


def test_group_prefix() -> None:
    assert sa.group_prefix("file.txt", 1) == "(root)"
    assert sa.group_prefix("logs/a.txt", 1) == "logs/"
    assert sa.group_prefix("logs/2024/a.txt", 1) == "logs/"
    assert sa.group_prefix("logs/2024/a.txt", 2) == "logs/2024/"
    assert sa.group_prefix("logs/2024/a.txt", 3) == "(root)"  # depth equal to parts => root


def test_format_size() -> None:
    assert sa.format_size(0) == "0.00 B"
    assert sa.format_size(1023) == "1023.00 B"
    assert sa.format_size(1024) == "1.00 KB"
    assert sa.format_size(1024**2) == "1.00 MB"
    assert sa.format_size(1024**3) == "1.00 GB"


def _fake_b2(versions_output: str, unfinished_output: str = "") -> Callable[[list[str]], str]:
    """Builds a side_effect that routes the two b2 subcommands the audit invokes."""

    def side_effect(args: list[str]) -> str:
        if args[:2] == ["ls", "--versions"]:
            return versions_output
        if args[:4] == ["file", "large", "unfinished", "list"]:
            # B2 CLI v4 requires `b2://<bucket>` URI form here.
            assert len(args) == 5 and args[4].startswith(
                "b2://"
            ), f"Expected `b2://<bucket>` URI; got: {args[4:]!r}"
            return unfinished_output
        raise AssertionError(f"Unexpected b2 invocation: {args}")

    return side_effect


def test_audit_splits_live_from_old_versions() -> None:
    versions: list[dict[str, Any]] = [
        # Two versions of the same file — newer wins as live.
        {
            "fileName": "a.txt",
            "contentLength": 200,
            "uploadTimestamp": _ts(5),
            "action": "upload",
            "contentSha1": "sha-new",
        },
        {
            "fileName": "a.txt",
            "contentLength": 100,
            "uploadTimestamp": _ts(50),
            "action": "upload",
            "contentSha1": "sha-old",
        },
        # Unique live file
        {
            "fileName": "b.txt",
            "contentLength": 300,
            "uploadTimestamp": _ts(3),
            "action": "upload",
            "contentSha1": "sha-b",
        },
    ]
    with patch.object(sa, "run_b2", side_effect=_fake_b2(json.dumps(versions))):
        report = sa.audit(
            "bucket", stale_days=90, large_mb=100, prefix_depth=1, price_per_gb_month=0.006
        )

    assert report["counts"]["live_files"] == 2
    assert report["counts"]["old_versions"] == 1
    assert report["sizes_bytes"]["live"] == 500  # 200 + 300
    assert report["sizes_bytes"]["old_versions"] == 100
    assert report["sizes_bytes"]["total_billable"] == 600


def test_audit_detects_hide_markers() -> None:
    versions: list[dict[str, Any]] = [
        {
            "fileName": "kept.txt",
            "contentLength": 100,
            "uploadTimestamp": _ts(5),
            "action": "upload",
            "contentSha1": "sha1",
        },
        {"fileName": "gone.txt", "contentLength": 0, "uploadTimestamp": _ts(2), "action": "hide"},
    ]
    with patch.object(sa, "run_b2", side_effect=_fake_b2(json.dumps(versions))):
        report = sa.audit("bucket", 90, 100, 1, 0.006)

    assert report["counts"]["hide_markers"] == 1
    assert report["counts"]["live_files"] == 1


def test_audit_stale_and_large_thresholds() -> None:
    versions: list[dict[str, Any]] = [
        {
            "fileName": "old.log",
            "contentLength": 10,
            "uploadTimestamp": _ts(120),
            "action": "upload",
            "contentSha1": "s1",
        },
        {
            "fileName": "new.log",
            "contentLength": 10,
            "uploadTimestamp": _ts(1),
            "action": "upload",
            "contentSha1": "s2",
        },
        {
            "fileName": "big.bin",
            "contentLength": 150 * 1024 * 1024,
            "uploadTimestamp": _ts(1),
            "action": "upload",
            "contentSha1": "s3",
        },
    ]
    with patch.object(sa, "run_b2", side_effect=_fake_b2(json.dumps(versions))):
        report = sa.audit(
            "bucket", stale_days=90, large_mb=100, prefix_depth=1, price_per_gb_month=0.006
        )

    assert len(report["stale_files"]) == 1
    assert report["stale_files"][0]["name"] == "old.log"
    assert len(report["large_files"]) == 1
    assert report["large_files"][0]["name"] == "big.bin"


def test_audit_detects_duplicates_by_sha1() -> None:
    versions: list[dict[str, Any]] = [
        {
            "fileName": "copy-a/photo.jpg",
            "contentLength": 1000,
            "uploadTimestamp": _ts(1),
            "action": "upload",
            "contentSha1": "DUP",
        },
        {
            "fileName": "copy-b/photo.jpg",
            "contentLength": 1000,
            "uploadTimestamp": _ts(1),
            "action": "upload",
            "contentSha1": "DUP",
        },
        {
            "fileName": "unique.bin",
            "contentLength": 1000,
            "uploadTimestamp": _ts(1),
            "action": "upload",
            "contentSha1": "UNIQUE",
        },
    ]
    with patch.object(sa, "run_b2", side_effect=_fake_b2(json.dumps(versions))):
        report = sa.audit("bucket", 90, 100, 1, 0.006)

    assert "DUP" in report["duplicates_by_sha1"]
    assert len(report["duplicates_by_sha1"]["DUP"]) == 2
    assert "UNIQUE" not in report["duplicates_by_sha1"]


def test_audit_skips_multipart_without_sha1() -> None:
    versions: list[dict[str, Any]] = [
        {
            "fileName": "big1.bin",
            "contentLength": 1000,
            "uploadTimestamp": _ts(1),
            "action": "upload",
            "contentSha1": "none",
        },
        {
            "fileName": "big2.bin",
            "contentLength": 1000,
            "uploadTimestamp": _ts(1),
            "action": "upload",
        },  # missing sha1
    ]
    with patch.object(sa, "run_b2", side_effect=_fake_b2(json.dumps(versions))):
        report = sa.audit("bucket", 90, 100, 1, 0.006)

    assert report["counts"]["files_without_sha1"] == 2
    assert report["duplicates_by_sha1"] == {}


def test_audit_cost_estimation() -> None:
    # 3 GB live (live.bin + newest stale.bin), 1 GB old versions → 4 GB billable
    versions: list[dict[str, Any]] = [
        {
            "fileName": "live.bin",
            "contentLength": 2 * 1024**3,
            "uploadTimestamp": _ts(1),
            "action": "upload",
            "contentSha1": "live",
        },
        {
            "fileName": "stale.bin",
            "contentLength": 1 * 1024**3,
            "uploadTimestamp": _ts(10),
            "action": "upload",
            "contentSha1": "s1",
        },
        {
            "fileName": "stale.bin",
            "contentLength": 1 * 1024**3,
            "uploadTimestamp": _ts(50),
            "action": "upload",
            "contentSha1": "s2",
        },
    ]
    with patch.object(sa, "run_b2", side_effect=_fake_b2(json.dumps(versions))):
        report = sa.audit("bucket", 90, 10_000, 1, 0.006)

    # 4 GB total billable * $0.006 = $0.024
    assert report["monthly_cost_usd"]["total_estimated"] == pytest.approx(0.024, abs=1e-4)
    # 1 GB old versions * $0.006 = $0.006 potential savings
    assert report["monthly_cost_usd"]["savings_if_cleanup"] == pytest.approx(0.006, abs=1e-4)


def test_list_unfinished_returns_empty_when_command_fails() -> None:
    def raise_called_process(args: list[str]) -> str:
        raise subprocess.CalledProcessError(1, args)

    with patch.object(sa, "run_b2", side_effect=raise_called_process):
        assert sa.list_unfinished("bucket") == []


def test_list_unfinished_passes_b2_uri() -> None:
    """B2 CLI v4 rejects bare bucket names with `Invalid B2 URI`; ensure we send the URI."""
    with patch.object(sa, "run_b2", return_value="") as mock_run:
        sa.list_unfinished("test-bucket")

    mock_run.assert_called_once_with(["file", "large", "unfinished", "list", "b2://test-bucket"])


def test_list_unfinished_parses_three_field_lines() -> None:
    """`<fileId> <fileName> <size>` — keep fileName, parse size as int."""
    output = "abc123  uploads/big.bin  104857600\n"
    with patch.object(sa, "run_b2", side_effect=_fake_b2("", output)):
        entries = sa.list_unfinished("bucket")

    assert entries == [{"fileId": "abc123", "fileName": "uploads/big.bin", "size": 104857600}]


def test_list_unfinished_parses_two_field_lines_without_size() -> None:
    """`<fileId> <fileName>` — size defaults to 0."""
    output = "abc123  uploads/big.bin\n"
    with patch.object(sa, "run_b2", side_effect=_fake_b2("", output)):
        entries = sa.list_unfinished("bucket")

    assert entries == [{"fileId": "abc123", "fileName": "uploads/big.bin", "size": 0}]


def test_list_unfinished_handles_filename_with_spaces() -> None:
    """File names containing spaces should not be split; size still parsed when numeric."""
    output = "abc123  path/with spaces/file.bin  1024\n"
    with patch.object(sa, "run_b2", side_effect=_fake_b2("", output)):
        entries = sa.list_unfinished("bucket")

    assert entries == [{"fileId": "abc123", "fileName": "path/with spaces/file.bin", "size": 1024}]
