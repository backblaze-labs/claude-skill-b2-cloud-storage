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
    GITHUB_TOKEN=ghp_... python scripts/check_listings_api.py     # higher rate limits

Exit codes:
  0 — every probe completed (live or not_found, no errors)
  1 — at least one probe errored (network, HTTP 5xx, etc.)
  2 — ``--strict`` is set and a hard expectation failed (e.g. repo missing
      required topics)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

REPO_SLUG = "backblaze-labs/claude-skill-b2-cloud-storage"
SKILL_NAME = "b2-cloud-storage"

# Topics that drive marketplace auto-discovery. Missing any of these is a
# concrete, fixable cause of "we're not listed anywhere."
EXPECTED_TOPICS = ("skillsmp", "claude-skill", "agent-skill", "claude-code")

MATCH_TERMS = (
    REPO_SLUG.lower(),
    "claude-skill-b2-cloud-storage",
)

USER_AGENT = (
    "claude-skill-b2-cloud-storage-listing-check/1.0 "
    "(+https://github.com/backblaze-labs/claude-skill-b2-cloud-storage)"
)

Status = Literal["live", "not_found", "error", "missing_topic"]


@dataclass
class Result:
    name: str
    url: str
    status: Status
    detail: str | None = None
    matched_term: str | None = None
    duration_ms: int = 0
    extras: dict[str, object] = field(default_factory=dict)


def _http_get(
    url: str, *, headers: dict[str, str] | None = None, timeout: int = 15
) -> tuple[int, str, dict[str, str]]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return resp.status, body, dict(resp.headers)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        return e.code, body, dict(e.headers or {})


def _scan(text: str, terms: tuple[str, ...]) -> str | None:
    haystack = text.lower()
    for term in terms:
        if term.lower() in haystack:
            return term
    return None


def check_github_repo() -> Result:
    """Hit api.github.com for repo metadata. Flags missing topics."""
    started = datetime.now(timezone.utc)
    name = "GitHub repo metadata"
    url = f"https://api.github.com/repos/{REPO_SLUG}"
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        code, body, _ = _http_get(url, headers=headers)
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        if code != 200:
            return Result(name, url, "error", detail=f"HTTP {code}", duration_ms=elapsed)
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
        }
        if missing:
            return Result(
                name,
                url,
                "missing_topic",
                detail=f"missing topics: {', '.join(missing)}",
                duration_ms=elapsed,
                extras=extras,
            )
        return Result(
            name,
            url,
            "live",
            detail=f"{data.get('stargazers_count', 0)}★ • topics ok",
            duration_ms=elapsed,
            extras=extras,
        )
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return Result(
            name, url, "error", detail=f"{type(exc).__name__}: {exc}", duration_ms=elapsed
        )


def check_text_probe(name: str, url: str, terms: tuple[str, ...] = MATCH_TERMS) -> Result:
    """Fetch a URL, grep for any of `terms`."""
    started = datetime.now(timezone.utc)
    try:
        code, body, _ = _http_get(url)
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        if code >= 400:
            return Result(name, url, "error", detail=f"HTTP {code}", duration_ms=elapsed)
        matched = _scan(body, terms)
        if matched:
            return Result(name, url, "live", matched_term=matched, duration_ms=elapsed)
        return Result(name, url, "not_found", duration_ms=elapsed)
    except (urllib.error.URLError, TimeoutError) as exc:
        elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return Result(
            name, url, "error", detail=f"{type(exc).__name__}: {exc}", duration_ms=elapsed
        )


# Probes that are fully checkable via plain HTTP (text grep). For SPAs,
# defer to scripts/check_listings.py.
TEXT_PROBES: tuple[tuple[str, str], ...] = (
    # Awesome lists
    (
        "Awesome Claude Skills (travisvn)",
        "https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md",
    ),
    (
        "Awesome Claude Plugins (Chat2AnyLLM)",
        "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-claude-plugins/main/README.md",
    ),
    (
        "Awesome Agent Skills (heilcheng)",
        "https://raw.githubusercontent.com/heilcheng/awesome-agent-skills/main/README.md",
    ),
    # Anthropic-managed directories
    (
        "Anthropic claude-plugins-official",
        "https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/README.md",
    ),
    (
        "Anthropic skills",
        "https://raw.githubusercontent.com/anthropics/skills/main/README.md",
    ),
    # Community marketplaces with public READMEs
    (
        "alirezarezvani/claude-skills",
        "https://raw.githubusercontent.com/alirezarezvani/claude-skills/main/README.md",
    ),
    (
        "daymade/claude-code-skills",
        "https://raw.githubusercontent.com/daymade/claude-code-skills/main/README.md",
    ),
    (
        "mhattingpete/claude-skills-marketplace",
        "https://raw.githubusercontent.com/mhattingpete/claude-skills-marketplace/main/README.md",
    ),
    # Tier-1 aggregators added 2026-05 — verified default branches per repo.
    # ComposioHQ uses `master`; everyone else here uses `main`.
    (
        "VoltAgent/awesome-agent-skills",
        "https://raw.githubusercontent.com/VoltAgent/awesome-agent-skills/main/README.md",
    ),
    (
        "hesreallyhim/awesome-claude-code",
        "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md",
    ),
    (
        "ComposioHQ/awesome-claude-skills",
        "https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/README.md",
    ),
    (
        "netresearch/claude-code-marketplace (README)",
        "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/README.md",
    ),
    # The marketplace.json is the authoritative source — README may lag.
    (
        "netresearch/claude-code-marketplace (manifest)",
        "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/.claude-plugin/marketplace.json",
    ),
    # Tier-2 community lists
    (
        "rohitg00/awesome-claude-code-toolkit",
        "https://raw.githubusercontent.com/rohitg00/awesome-claude-code-toolkit/main/README.md",
    ),
    (
        "BehiSecc/awesome-claude-skills",
        "https://raw.githubusercontent.com/BehiSecc/awesome-claude-skills/main/README.md",
    ),
    (
        "jqueryscript/awesome-claude-code",
        "https://raw.githubusercontent.com/jqueryscript/awesome-claude-code/main/README.md",
    ),
    # SPAs — best-effort HTML grep. May produce false negatives if listings
    # are rendered client-side; trust the Playwright probe for those.
    (
        "SkillsMP (HTML)",
        "https://skillsmp.com/?q=backblaze",
    ),
    (
        "LobeHub Skills (HTML)",
        "https://lobehub.com/skills?q=backblaze",
    ),
    (
        "Claude Marketplaces (HTML)",
        "https://claudemarketplaces.com/",
    ),
    (
        "Cult of Claude (HTML)",
        "https://cultofclaude.com/skills/?s=backblaze",
    ),
)


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    parser.add_argument("--report", type=Path, help="Also write the markdown report to this path")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit nonzero on missing GitHub topics (in addition to errors)",
    )
    args = parser.parse_args()

    results: list[Result] = [check_github_repo()]
    for name, url in TEXT_PROBES:
        print(f"  → {name}  …  ", end="", flush=True, file=sys.stderr)
        r = check_text_probe(name, url)
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

    has_error = any(r.status == "error" for r in results)
    has_missing_topic = any(r.status == "missing_topic" for r in results)
    if has_error:
        return 1
    if args.strict and has_missing_topic:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
