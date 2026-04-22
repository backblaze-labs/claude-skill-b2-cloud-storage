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

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath

# Current as of 2026-04. See https://www.backblaze.com/cloud-storage/pricing
DEFAULT_PRICE_PER_GB_MONTH = 0.006


def run_b2(args):
    """Run `b2 <args>` and return stdout. Raises CalledProcessError on failure."""
    return subprocess.run(
        ["b2", *args],
        capture_output=True, text=True, check=True,
    ).stdout


def list_versions(bucket):
    """All file versions including hide markers, via `b2 ls --versions`."""
    out = run_b2(["ls", "--versions", "-r", "--json", f"b2://{bucket}"]).strip()
    if not out:
        return []
    return json.loads(out)


def list_unfinished(bucket):
    """Unfinished large uploads. Returns [] if the subcommand is unavailable or fails."""
    try:
        out = run_b2(["file", "large", "unfinished", "list", bucket]).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    entries = []
    # Output format is one file per line: <fileId> <fileName> [<size>]
    # Be liberal — just record what we can parse.
    for line in out.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 2:
            entries.append({
                "fileId": parts[0],
                "fileName": parts[1] if len(parts) == 2 else parts[2],
                "size": 0,  # size not always present in CLI output
            })
    return entries


def group_prefix(name, depth):
    parts = name.split("/")
    if len(parts) <= depth:
        return "(root)"
    return "/".join(parts[:depth]) + "/"


def audit(bucket, stale_days, large_mb, prefix_depth, price_per_gb_month):
    now = datetime.now(timezone.utc)
    large_bytes = large_mb * 1024 * 1024

    versions = list_versions(bucket)
    unfinished = list_unfinished(bucket)

    # Separate by action. B2 file-versions emits action ∈ {upload, hide, start, folder}.
    # "start" should be rare here since unfinished are listed separately, but handle it.
    uploads = []
    hide_markers = []
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
    latest = {}
    old_versions = []
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

    def size_of(f):
        return f.get("contentLength", f.get("size", 0)) or 0

    live_size = sum(size_of(f) for f in live_files)
    old_version_size = sum(size_of(f) for f in old_versions)
    hide_marker_size = sum(size_of(f) for f in hide_markers)  # typically 0
    unfinished_size = sum(size_of(f) for f in unfinished)
    total_billable = live_size + old_version_size + unfinished_size

    # Live-file tallies
    prefix_sizes = defaultdict(int)
    ext_sizes = defaultdict(int)
    ext_counts = defaultdict(int)
    stale = []
    large = []
    sha1_groups = defaultdict(list)
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

    gb = 1024 ** 3
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


def format_size(b):
    b = float(b)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} PB"


def print_report(r):
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
    for ext, info in list(r["by_extension"].items())[:15]:
        print(f"  {ext:10s}  {info['count']:>7d} files  {format_size(info['size_bytes']):>12s}")

    if r["stale_files"]:
        print(f"\n--- Stale Files (>{t['stale_days']} days): {len(r['stale_files'])} ---")
        for f in r["stale_files"][:20]:
            print(f"  {f['name']}  ({f['age_days']}d, {format_size(f['size'])})")
        if len(r["stale_files"]) > 20:
            print(f"  ... and {len(r['stale_files']) - 20} more")

    if r["large_files"]:
        print(f"\n--- Large Files (>{t['large_mb']} MB): {len(r['large_files'])} ---")
        for f in r["large_files"][:20]:
            print(f"  {f['name']}  ({format_size(f['size'])})")

    if r["duplicates_by_sha1"]:
        print(f"\n--- Duplicates by contentSha1: {len(r['duplicates_by_sha1'])} groups ---")
        for sha, paths in list(r["duplicates_by_sha1"].items())[:10]:
            print(f"  {sha[:12]}…")
            for p in paths:
                print(f"    - {p}")
        if c["files_without_sha1"]:
            print(f"  ({c['files_without_sha1']} files had no contentSha1 — likely multipart uploads; skipped)")


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("bucket")
    p.add_argument("--stale-days", type=int, default=90)
    p.add_argument("--large-mb", type=int, default=100)
    p.add_argument("--prefix-depth", type=int, default=1,
                   help="Path depth for prefix grouping (1 = first path component)")
    p.add_argument("--price-per-gb-month", type=float, default=DEFAULT_PRICE_PER_GB_MONTH)
    p.add_argument("--json", action="store_true", help="Emit JSON report instead of pretty text")
    args = p.parse_args()

    try:
        report = audit(
            args.bucket, args.stale_days, args.large_mb,
            args.prefix_depth, args.price_per_gb_month,
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
