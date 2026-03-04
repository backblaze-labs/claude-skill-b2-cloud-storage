#!/usr/bin/env python3
"""B2 bucket storage audit — aggregates files by prefix, extension, and age."""

import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import PurePosixPath


def run_audit(bucket: str) -> dict:
    result = subprocess.run(
        ["b2", "ls", "-r", "--json", f"b2://{bucket}"],
        capture_output=True, text=True, check=True,
    )

    output = result.stdout.strip()
    try:
        parsed = json.loads(output)
        files = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        files = [json.loads(line) for line in output.splitlines() if line.strip()]
    now = datetime.now(timezone.utc)

    total_size = 0
    prefix_sizes = defaultdict(int)
    ext_sizes = defaultdict(int)
    ext_counts = defaultdict(int)
    stale_files = []  # >90 days old
    large_files = []  # >100 MB
    basenames = defaultdict(list)  # basename -> list of full paths (duplicate detection)

    for f in files:
        name = f.get("fileName", "")
        size = f.get("contentLength", f.get("size", 0))
        upload_ts = f.get("uploadTimestamp", 0) / 1000  # ms -> s

        total_size += size

        # prefix = first path component
        parts = name.split("/")
        prefix = parts[0] if len(parts) > 1 else "(root)"
        prefix_sizes[prefix] += size

        # extension
        ext = PurePosixPath(name).suffix.lower() or "(none)"
        ext_sizes[ext] += size
        ext_counts[ext] += 1

        # age check
        if upload_ts:
            age_days = (now - datetime.fromtimestamp(upload_ts, tz=timezone.utc)).days
            if age_days > 90:
                stale_files.append({"name": name, "size": size, "age_days": age_days})

        # large file check
        if size > 100 * 1024 * 1024:
            large_files.append({"name": name, "size": size})

        # duplicate detection by basename
        basename = PurePosixPath(name).name
        basenames[basename].append(name)

    duplicates = {k: v for k, v in basenames.items() if len(v) > 1}

    report = {
        "bucket": bucket,
        "total_files": len(files),
        "total_size_bytes": total_size,
        "total_size_gb": round(total_size / (1024 ** 3), 3),
        "by_prefix": {
            k: {"size_bytes": v, "size_gb": round(v / (1024 ** 3), 3)}
            for k, v in sorted(prefix_sizes.items(), key=lambda x: -x[1])
        },
        "by_extension": {
            k: {"count": ext_counts[k], "size_bytes": v, "size_gb": round(v / (1024 ** 3), 3)}
            for k, v in sorted(ext_sizes.items(), key=lambda x: -x[1])
        },
        "stale_files_over_90_days": sorted(stale_files, key=lambda x: -x["age_days"]),
        "large_files_over_100mb": sorted(large_files, key=lambda x: -x["size"]),
        "potential_duplicates": duplicates,
    }
    return report


def format_size(b: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if b < 1024:
            return f"{b:.2f} {unit}"
        b /= 1024
    return f"{b:.2f} PB"


def print_report(report: dict) -> None:
    print(f"\n=== Storage Audit: {report['bucket']} ===\n")
    print(f"Total files:  {report['total_files']}")
    print(f"Total size:   {format_size(report['total_size_bytes'])} ({report['total_size_gb']} GB)")

    print("\n--- By Prefix ---")
    for prefix, info in report["by_prefix"].items():
        print(f"  {prefix:30s}  {format_size(info['size_bytes']):>12s}")

    print("\n--- By Extension ---")
    for ext, info in report["by_extension"].items():
        print(f"  {ext:10s}  {info['count']:>6d} files  {format_size(info['size_bytes']):>12s}")

    if report["stale_files_over_90_days"]:
        print(f"\n--- Stale Files (>90 days): {len(report['stale_files_over_90_days'])} ---")
        for f in report["stale_files_over_90_days"][:20]:
            print(f"  {f['name']}  ({f['age_days']}d, {format_size(f['size'])})")
        if len(report["stale_files_over_90_days"]) > 20:
            print(f"  ... and {len(report['stale_files_over_90_days']) - 20} more")

    if report["large_files_over_100mb"]:
        print(f"\n--- Large Files (>100MB): {len(report['large_files_over_100mb'])} ---")
        for f in report["large_files_over_100mb"]:
            print(f"  {f['name']}  ({format_size(f['size'])})")

    if report["potential_duplicates"]:
        print(f"\n--- Potential Duplicates: {len(report['potential_duplicates'])} basenames ---")
        for basename, paths in list(report["potential_duplicates"].items())[:10]:
            print(f"  {basename}:")
            for p in paths:
                print(f"    - {p}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <bucket-name>", file=sys.stderr)
        sys.exit(1)
    report = run_audit(sys.argv[1])
    print_report(report)
