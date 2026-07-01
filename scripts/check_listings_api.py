#!/usr/bin/env python3
"""Pure-stdlib listing check — fast, no browser, suitable for CI / cron.

Companion to ``check_listings.py``. The Playwright script is the source of
truth for SPA-rendered marketplace pages; this script covers everything that
can be checked with plain HTTP:

  * GitHub repo metadata for ``backblaze-labs/claude-skill-b2-cloud-storage``
    (topics, stars, archived flag) — answers "did anyone forget to add the
    ``skillsmp`` topic?"
  * Raw README of every awesome-list / community marketplace that aggregates
    skills from GitHub. Plain text grep — zero false positives.
  * Anthropic's official skills/plugins directories (raw README).
  * SkillsMP, LobeHub, claudemarketplaces.com landing pages — best-effort
    HTML grep. SPAs may hydrate after first paint, so a "not_found" here
    means "almost certainly not listed" but trust the Playwright probe for
    final confirmation.

Usage::

    python scripts/check_listings_api.py
    python scripts/check_listings_api.py --json
    python scripts/check_listings_api.py --report dist/listings-api.md
    GITHUB_TOKEN=your-token python scripts/check_listings_api.py  # higher rate limits

Exit codes:
  0 — every probe completed (live or not_found, no errors)
  1 — at least one probe errored (network, HTTP 5xx, etc.)
  2 — required GitHub topics are missing, or ``--strict`` cannot verify them
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from listing_catalog import HTTP_PROBES, REPO_SLUG, SKILL_NAME, HttpProbeSpec

# Topics that drive marketplace auto-discovery. Missing any of these is a
# concrete, fixable cause of "we're not listed anywhere."
EXPECTED_TOPICS = ("skillsmp", "claude-skill", "agent-skill", "claude-code")

USER_AGENT = (
    "claude-skill-b2-cloud-storage-listing-check/1.0 "
    "(+https://github.com/backblaze-labs/claude-skill-b2-cloud-storage)"
)

READ_CHUNK_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
HTTP_TIMEOUT_SECONDS = 15.0
HTTP_TOTAL_TIMEOUT_SECONDS = 20.0
GITHUB_RETRY_ATTEMPTS = 3
GITHUB_RETRY_BACKOFF_SECONDS = (1.0, 2.0)

Status = Literal["live", "not_found", "error", "missing_topic"]


class ResponseTooLarge(ValueError):
    """Raised when an HTTP response exceeds the configured body cap."""


@dataclass
class Result:
    name: str
    url: str
    status: Status
    detail: str | None = None
    matched_term: str | None = None
    duration_ms: int = 0
    extras: dict[str, object] = field(default_factory=dict)


def _set_response_read_timeout(response: object, timeout: float) -> None:
    for attr_path in (("fp", "raw", "_sock"), ("raw", "_sock"), ("_sock",)):
        current = response
        for attr in attr_path:
            current = getattr(current, attr, None)
            if current is None:
                break
        else:
            settimeout = getattr(current, "settimeout", None)
            if callable(settimeout):
                settimeout(max(timeout, 0.001))
                return


def _read_limited_body(
    response: object,
    *,
    max_bytes: int,
    deadline: float,
    headers: object | None = None,
) -> bytes:
    response_headers = headers if headers is not None else getattr(response, "headers", None)
    header_get = getattr(response_headers, "get", None)
    content_length = header_get("Content-Length") if callable(header_get) else None
    if content_length:
        try:
            if int(content_length) > max_bytes:
                msg = f"Content-Length {content_length} exceeds {max_bytes} byte limit"
                raise ResponseTooLarge(msg)
        except ValueError as exc:
            if isinstance(exc, ResponseTooLarge):
                raise

    chunks: list[bytes] = []
    total = 0
    while True:
        remaining_seconds = deadline - time.monotonic()
        if remaining_seconds <= 0:
            raise TimeoutError("response read deadline exceeded")
        _set_response_read_timeout(response, remaining_seconds)
        read_size = min(READ_CHUNK_BYTES, max_bytes + 1 - total)
        chunk = response.read(read_size)
        if not chunk:
            return b"".join(chunks)
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            msg = f"response exceeded {max_bytes} byte limit"
            raise ResponseTooLarge(msg)


def http_get_limited(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = HTTP_TIMEOUT_SECONDS,
    max_bytes: int = MAX_RESPONSE_BYTES,
    total_timeout: float = HTTP_TOTAL_TIMEOUT_SECONDS,
) -> tuple[int, str, dict[str, str]]:
    """Fetch a URL with bounded response size and total body-read time."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    deadline = time.monotonic() + total_timeout
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _read_limited_body(resp, max_bytes=max_bytes, deadline=deadline).decode(
                "utf-8", errors="replace"
            )
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = ""
        if e.fp:
            body = _read_limited_body(
                e.fp,
                max_bytes=max_bytes,
                deadline=deadline,
                headers=e.headers,
            ).decode("utf-8", errors="replace")
        return e.code, body, dict(e.headers or {})


def _scan(text: str, terms: tuple[str, ...]) -> str | None:
    haystack = text.lower()
    for term in terms:
        if term.lower() in haystack:
            return term
    return None


def _elapsed_ms(started: datetime) -> int:
    return int((datetime.now(timezone.utc) - started).total_seconds() * 1000)


def _is_retryable_status(code: int) -> bool:
    return code in (403, 429) or code >= 500


def _github_error_result(started: datetime, detail: str) -> Result:
    return Result(
        "GitHub repo metadata",
        f"https://api.github.com/repos/{REPO_SLUG}",
        "error",
        detail=f"GitHub metadata unavailable: {detail}",
        duration_ms=_elapsed_ms(started),
    )


def check_github_repo(
    *,
    attempts: int = GITHUB_RETRY_ATTEMPTS,
    backoff_seconds: tuple[float, ...] = GITHUB_RETRY_BACKOFF_SECONDS,
) -> Result:
    """Hit api.github.com for repo metadata. Flags missing topics."""
    started = datetime.now(timezone.utc)
    name = "GitHub repo metadata"
    url = f"https://api.github.com/repos/{REPO_SLUG}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    last_detail = "unknown error"
    for attempt in range(1, attempts + 1):
        try:
            code, body, _ = http_get_limited(url, headers=headers)
            if code != 200:
                last_detail = f"HTTP {code}"
                if attempt < attempts and _is_retryable_status(code):
                    time.sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
                    continue
                return _github_error_result(started, last_detail)

            data = json.loads(body)
            topics = tuple(data.get("topics") or ())
            missing = tuple(t for t in EXPECTED_TOPICS if t not in topics)
            extras: dict[str, object] = {
                "stars": data.get("stargazers_count"),
                "forks": data.get("forks_count"),
                "archived": data.get("archived"),
                "default_branch": data.get("default_branch"),
                "topics": topics,
                "missing_topics": missing,
                "description": data.get("description"),
                "attempts": attempt,
            }
            if missing:
                return Result(
                    name,
                    url,
                    "missing_topic",
                    detail=f"missing topics: {', '.join(missing)}",
                    duration_ms=_elapsed_ms(started),
                    extras=extras,
                )
            return Result(
                name,
                url,
                "live",
                detail=f"{data.get('stargazers_count', 0)}★ • topics ok",
                duration_ms=_elapsed_ms(started),
                extras=extras,
            )
        except (urllib.error.URLError, TimeoutError, ValueError) as exc:
            last_detail = f"{type(exc).__name__}: {exc}"
            if attempt < attempts:
                time.sleep(backoff_seconds[min(attempt - 1, len(backoff_seconds) - 1)])
                continue
            return _github_error_result(started, last_detail)

    return _github_error_result(started, last_detail)


def check_text_probe(probe: HttpProbeSpec) -> Result:
    """Fetch a URL, grep for any of `terms`."""
    started = datetime.now(timezone.utc)
    try:
        code, body, _ = http_get_limited(probe.url)
        elapsed = _elapsed_ms(started)
        if code >= 400:
            return Result(
                probe.name, probe.url, "error", detail=f"HTTP {code}", duration_ms=elapsed
            )
        matched = _scan(body, probe.match_terms)
        if matched:
            return Result(probe.name, probe.url, "live", matched_term=matched, duration_ms=elapsed)
        return Result(probe.name, probe.url, "not_found", duration_ms=elapsed)
    except (urllib.error.URLError, TimeoutError, ResponseTooLarge) as exc:
        elapsed = _elapsed_ms(started)
        return Result(
            probe.name,
            probe.url,
            "error",
            detail=f"{type(exc).__name__}: {exc}",
            duration_ms=elapsed,
        )


TEXT_PROBES = HTTP_PROBES


def render_markdown(results: list[Result]) -> str:
    icon = {"live": "✅", "not_found": "❌", "error": "⚠️", "missing_topic": "🏷️"}
    lines = [
        f"# Listing status (HTTP-only) — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Repo: `{REPO_SLUG}`  •  Skill: `{SKILL_NAME}`",
        "",
        "| Source | Status | Detail |",
        "|---|---|---|",
    ]
    for r in results:
        detail = r.detail or (f"matched: {r.matched_term}" if r.matched_term else "—")
        if len(detail) > 90:
            detail = detail[:87] + "…"
        lines.append(f"| {r.name} | {icon.get(r.status, '?')} {r.status} | {detail} |")

    live = sum(1 for r in results if r.status == "live")
    missing_topics = next((r for r in results if r.status == "missing_topic"), None)
    lines += ["", f"**{live}/{len(results)} live.**"]
    if missing_topics and isinstance(missing_topics.extras.get("missing_topics"), tuple):
        missing = missing_topics.extras["missing_topics"]
        if missing:
            lines += [
                "",
                "## Missing GitHub topics",
                "",
                "Add these topics to the repo to unlock auto-discovery on aggregators:",
                "",
                *(f"- `{t}`" for t in missing),
                "",
                'GitHub: Settings → "manage topics" on the repo landing page.',
            ]
    return "\n".join(lines)


def strict_topic_failures(results: list[Result]) -> list[str]:
    github = next((r for r in results if r.name == "GitHub repo metadata"), None)
    if github is None:
        return ["GitHub metadata result missing from probe output"]
    if github.status == "missing_topic":
        return [github.detail or "required GitHub discovery topics are missing"]
    if github.status == "error":
        return [github.detail or "GitHub metadata probe failed"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    parser.add_argument("--report", type=Path, help="Also write the markdown report to this path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit nonzero when the GitHub metadata probe is unavailable or required "
            "topics are missing; third-party marketplace errors remain report-only"
        ),
    )
    args = parser.parse_args()

    results: list[Result] = [check_github_repo()]
    for probe in TEXT_PROBES:
        print(f"  → {probe.name}  …  ", end="", flush=True, file=sys.stderr)
        r = check_text_probe(probe)
        results.append(r)
        tag = r.matched_term or r.detail or "—"
        print(f"{r.status}  ({r.duration_ms}ms)  {tag}", file=sys.stderr)

    md = render_markdown(results)
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2, default=str))
    else:
        print(md)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(md + "\n", encoding="utf-8")

    if args.strict:
        failures = strict_topic_failures(results)
        for failure in failures:
            print(f"::error::{failure}", file=sys.stderr)
        return 2 if failures else 0

    has_error = any(r.status == "error" for r in results)
    has_missing_topic = any(r.status == "missing_topic" for r in results)
    if has_error:
        return 1
    if has_missing_topic:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
