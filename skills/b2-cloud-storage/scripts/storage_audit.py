#!/usr/bin/env python3
"""B2 bucket storage audit.

Reports:
- Live vs. billable storage (live files, old versions, hide markers, unfinished uploads)
- Stale files (> --stale-days old)
- Large files (> --large-mb)
- Duplicate content (grouped by contentSha1 where available)
- Estimated monthly storage cost

Note: loads all file versions into memory via `b2 ls --versions -r --json`.
For buckets with >~1M file versions, shard by prefix or use the B2 API directly.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import TypedDict, cast

# Current as of 2026-04. See https://www.backblaze.com/cloud-storage/pricing
DEFAULT_PRICE_PER_GB_MONTH: float = 0.006


class B2FileVersion(TypedDict, total=False):
    """A single entry from `b2 ls --versions -r --json`, or a synthesized unfinished entry."""

    fileName: str
    fileId: str
    contentLength: int
    uploadTimestamp: int
    action: str  # "upload" | "hide" | "folder" | "start"
    contentSha1: str
    size: int  # used by synthesized unfinished entries


class Thresholds(TypedDict):
    stale_days: int
    large_mb: int
    prefix_depth: int


class Counts(TypedDict):
    live_files: int
    old_versions: int
    hide_markers: int
    unfinished_uploads: int
    files_without_sha1: int


class SizesBytes(TypedDict):
    live: int
    old_versions: int
    hide_markers: int
    unfinished_uploads: int
    total_billable: int


class MonthlyCost(TypedDict):
    total_estimated: float
    savings_if_cleanup: float
    price_per_gb_month: float


class PrefixInfo(TypedDict):
    size_bytes: int
    size_gb: float


class ExtensionInfo(TypedDict):
    count: int
    size_bytes: int
    size_gb: float


class StaleEntry(TypedDict):
    name: str
    size: int
    age_days: int


class LargeEntry(TypedDict):
    name: str
    size: int


class AuditReport(TypedDict):
    bucket: str
    thresholds: Thresholds
    counts: Counts
    sizes_bytes: SizesBytes
    monthly_cost_usd: MonthlyCost
    by_prefix: dict[str, PrefixInfo]
    by_extension: dict[str, ExtensionInfo]
    stale_files: list[StaleEntry]
    large_files: list[LargeEntry]
    duplicates_by_sha1: dict[str, list[str]]


def run_b2(args: list[str]) -> str:
    """Run `b2 <args>` and return stdout. Raises CalledProcessError on failure."""
    return subprocess.run(
        ["b2", *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def list_versions(bucket: str) -> list[B2FileVersion]:
    """All file versions including hide markers, via `b2 ls --versions`."""
    out = run_b2(["ls", "--versions", "-r", "--json", f"b2://{bucket}"]).strip()
    if not out:
        return []
    return cast(list[B2FileVersion], json.loads(out))


def list_unfinished(bucket: str) -> list[B2FileVersion]:
    """Unfinished large uploads. Returns [] if the subcommand is unavailable or fails.

    The bucket must be passed as a `b2://<bucket>` URI — B2 CLI v4 rejects bare
    bucket names with `Invalid B2 URI` before authentication.
    """
    try:
        out = run_b2(["file", "large", "unfinished", "list", f"b2://{bucket}"]).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    entries: list[B2FileVersion] = []
    # Output format is one file per line: <fileId> <fileName> [<size>]
    # The size is optional and numeric when present; fileName may contain
    # spaces, so reconstruct it from middle tokens. Be liberal — just record
    # what we can parse.
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        file_id = parts[0]
        if len(parts) >= 3 and parts[-1].isdigit():
            file_name = " ".join(parts[1:-1])
            size = int(parts[-1])
        else:
            file_name = " ".join(parts[1:])
            size = 0
        entries.append({"fileId": file_id, "fileName": file_name, "size": size})
    return entries


def group_prefix(name: str, depth: int) -> str:
    parts = name.split("/")
    if len(parts) <= depth:
        return "(root)"
    return "/".join(parts[:depth]) + "/"


def audit(
    bucket: str,
    stale_days: int,
    large_mb: int,
    prefix_depth: int,
    price_per_gb_month: float,
) -> AuditReport:
    now = datetime.now(timezone.utc)
    large_bytes = large_mb * 1024 * 1024

    versions = list_versions(bucket)
    unfinished = list_unfinished(bucket)

    # Separate by action. B2 file-versions emits action ∈ {upload, hide, start, folder}.
    # "start" should be rare here since unfinished are listed separately, but handle it.
    uploads: list[B2FileVersion] = []
    hide_markers: list[B2FileVersion] = []
    for f in versions:
        action = f.get("action")
        if action == "folder":
            continue
        if action == "hide":
            hide_markers.append(f)
        elif action in (None, "upload"):
            uploads.append(f)
        # ignore "start" — covered by list_unfinished

    # For each fileName, the highest uploadTimestamp is the live version; others are old.
    latest: dict[str, B2FileVersion] = {}
    old_versions: list[B2FileVersion] = []
    for f in uploads:
        name = f.get("fileName", "")
        ts = f.get("uploadTimestamp", 0)
        if name not in latest:
            latest[name] = f
        elif ts > latest[name].get("uploadTimestamp", 0):
            old_versions.append(latest[name])
            latest[name] = f
        else:
            old_versions.append(f)
    live_files = list(latest.values())

    def size_of(f: B2FileVersion) -> int:
        return f.get("contentLength", f.get("size", 0)) or 0

    live_size = sum(size_of(f) for f in live_files)
    old_version_size = sum(size_of(f) for f in old_versions)
    hide_marker_size = sum(size_of(f) for f in hide_markers)  # typically 0
    unfinished_size = sum(size_of(f) for f in unfinished)
    # B2 bills every stored file version, including hide markers. Their reported
    # size is usually 0, but include it so we don't under-report if that ever changes.
    total_billable = live_size + old_version_size + hide_marker_size + unfinished_size

    # Live-file tallies
    prefix_sizes: dict[str, int] = defaultdict(int)
    ext_sizes: dict[str, int] = defaultdict(int)
    ext_counts: dict[str, int] = defaultdict(int)
    stale: list[StaleEntry] = []
    large: list[LargeEntry] = []
    sha1_groups: dict[str, list[str]] = defaultdict(list)
    unknown_sha_count = 0

    for f in live_files:
        name = f.get("fileName", "")
        size = size_of(f)
        ts_ms = f.get("uploadTimestamp", 0)

        prefix_sizes[group_prefix(name, prefix_depth)] += size

        ext = PurePosixPath(name).suffix.lower() or "(none)"
        ext_sizes[ext] += size
        ext_counts[ext] += 1

        if ts_ms:
            age_days = (now - datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)).days
            if age_days > stale_days:
                stale.append({"name": name, "size": size, "age_days": age_days})

        if size > large_bytes:
            large.append({"name": name, "size": size})

        sha = f.get("contentSha1")
        if sha and sha != "none":
            sha1_groups[sha].append(name)
        else:
            unknown_sha_count += 1

    duplicates = {sha: names for sha, names in sha1_groups.items() if len(names) > 1}

    gb = 1024**3
    monthly_cost = (total_billable / gb) * price_per_gb_month
    savings_if_cleanup = ((old_version_size + unfinished_size) / gb) * price_per_gb_month

    return {
        "bucket": bucket,
        "thresholds": {
            "stale_days": stale_days,
            "large_mb": large_mb,
            "prefix_depth": prefix_depth,
        },
        "counts": {
            "live_files": len(live_files),
            "old_versions": len(old_versions),
            "hide_markers": len(hide_markers),
            "unfinished_uploads": len(unfinished),
            "files_without_sha1": unknown_sha_count,
        },
        "sizes_bytes": {
            "live": live_size,
            "old_versions": old_version_size,
            "hide_markers": hide_marker_size,
            "unfinished_uploads": unfinished_size,
            "total_billable": total_billable,
        },
        "monthly_cost_usd": {
            "total_estimated": round(monthly_cost, 4),
            "savings_if_cleanup": round(savings_if_cleanup, 4),
            "price_per_gb_month": price_per_gb_month,
        },
        "by_prefix": {
            k: {"size_bytes": v, "size_gb": round(v / gb, 3)}
            for k, v in sorted(prefix_sizes.items(), key=lambda x: -x[1])
        },
        "by_extension": {
            k: {"count": ext_counts[k], "size_bytes": v, "size_gb": round(v / gb, 3)}
            for k, v in sorted(ext_sizes.items(), key=lambda x: -x[1])
        },
        "stale_files": sorted(stale, key=lambda x: -x["age_days"]),
        "large_files": sorted(large, key=lambda x: -x["size"]),
        "duplicates_by_sha1": duplicates,
    }


def format_size(b: float | int) -> str:
    bf = float(b)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bf < 1024:
            return f"{bf:.2f} {unit}"
        bf /= 1024
    return f"{bf:.2f} PB"


def print_report(r: AuditReport) -> None:
    t = r["thresholds"]
    c = r["counts"]
    s = r["sizes_bytes"]
    cost = r["monthly_cost_usd"]

    print(f"\n=== Storage Audit: {r['bucket']} ===\n")
    print(f"Live files:            {c['live_files']}")
    print(f"Old versions:          {c['old_versions']}")
    print(f"Hide markers:          {c['hide_markers']}")
    print(f"Unfinished uploads:    {c['unfinished_uploads']}")

    print("\n--- Storage ---")
    print(f"  Live:               {format_size(s['live'])}")
    print(f"  Old versions:       {format_size(s['old_versions'])}")
    print(f"  Unfinished uploads: {format_size(s['unfinished_uploads'])}")
    print(f"  Total billable:     {format_size(s['total_billable'])}")

    print("\n--- Estimated monthly cost (storage only) ---")
    print(f"  @ ${cost['price_per_gb_month']}/GB-month: ${cost['total_estimated']:.2f}")
    if cost["savings_if_cleanup"] > 0.01:
        print(f"  Potential savings after cleanup: ${cost['savings_if_cleanup']:.2f}/mo")

    print("\n--- By Prefix (live files) ---")
    for prefix, info in list(r["by_prefix"].items())[:20]:
        print(f"  {prefix:40s}  {format_size(info['size_bytes']):>12s}")

    print("\n--- By Extension (live files) ---")
    for ext, ext_info in list(r["by_extension"].items())[:15]:
        print(
            f"  {ext:10s}  {ext_info['count']:>7d} files  "
            f"{format_size(ext_info['size_bytes']):>12s}"
        )

    if r["stale_files"]:
        print(f"\n--- Stale Files (>{t['stale_days']} days): {len(r['stale_files'])} ---")
        for sf in r["stale_files"][:20]:
            print(f"  {sf['name']}  ({sf['age_days']}d, {format_size(sf['size'])})")
        if len(r["stale_files"]) > 20:
            print(f"  ... and {len(r['stale_files']) - 20} more")

    if r["large_files"]:
        print(f"\n--- Large Files (>{t['large_mb']} MB): {len(r['large_files'])} ---")
        for lf in r["large_files"][:20]:
            print(f"  {lf['name']}  ({format_size(lf['size'])})")

    if r["duplicates_by_sha1"]:
        print(f"\n--- Duplicates by contentSha1: {len(r['duplicates_by_sha1'])} groups ---")
        for sha, paths in list(r["duplicates_by_sha1"].items())[:10]:
            print(f"  {sha[:12]}…")
            for p in paths:
                print(f"    - {p}")
        if c["files_without_sha1"]:
            print(
                f"  ({c['files_without_sha1']} files had no contentSha1 — "
                "likely multipart uploads; skipped)"
            )


def main() -> None:
    p = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    p.add_argument("bucket")
    p.add_argument("--stale-days", type=int, default=90)
    p.add_argument("--large-mb", type=int, default=100)
    p.add_argument(
        "--prefix-depth",
        type=int,
        default=1,
        help="Path depth for prefix grouping (1 = first path component)",
    )
    p.add_argument("--price-per-gb-month", type=float, default=DEFAULT_PRICE_PER_GB_MONTH)
    p.add_argument("--json", action="store_true", help="Emit JSON report instead of pretty text")
    args = p.parse_args()

    try:
        report = audit(
            args.bucket,
            args.stale_days,
            args.large_mb,
            args.prefix_depth,
            args.price_per_gb_month,
        )
    except subprocess.CalledProcessError as e:
        print(f"b2 CLI failed: {e.stderr or e}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)


if __name__ == "__main__":
    main()
