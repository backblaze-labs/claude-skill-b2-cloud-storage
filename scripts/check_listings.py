#!/usr/bin/env python3
"""Probe each skill directory and report whether our skill is listed.

Local setup (one-time):

    pip install playwright
    playwright install chromium

Usage:

    python scripts/check_listings.py                  # headless, all probes
    python scripts/check_listings.py --headed         # show the browser
    python scripts/check_listings.py --only LobeHub   # one directory
    python scripts/check_listings.py --json           # machine-readable
    python scripts/check_listings.py --screenshots    # save evidence to dist/listing-checks/

The intent is exploratory: navigate to each directory's search/listing URL,
look for our skill in the rendered page text, and report. Selectors are
deliberately loose because every site is laid out differently and many are
SPAs — we trust the visible text after `networkidle`. Iterate by tightening
probes for sites that surface false positives or false negatives.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

try:
    from playwright.sync_api import Page, sync_playwright
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
except ImportError:  # pragma: no cover
    sys.exit(
        "playwright is not installed. Run:\n"
        "    pip install playwright && playwright install chromium"
    )

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "dist" / "listing-checks"

REPO_SLUG = "backblaze-labs/claude-skill-b2-cloud-storage"
SKILL_NAME = "b2-cloud-storage"

# Phrases we accept as proof of listing. Any one match flips status to "live".
# Bare "backblaze" was too broad — query echoes ("matching 'backblaze'") tripped it.
MATCH_TERMS = (
    "backblaze-labs/claude-skill-b2-cloud-storage",
    "claude-skill-b2-cloud-storage",
    "b2-cloud-storage",
)

Status = Literal["live", "not_found", "error", "blocked"]

# Selectors tried in order when a probe needs interactive search. The first
# locator that becomes visible wins. Add per-probe overrides via Probe.search_locators.
DEFAULT_SEARCH_LOCATORS: tuple[str, ...] = (
    "input[type='search']",
    "[role='searchbox']",
    "input[placeholder*='Search' i]",
    "input[name='q']",
    "input[name='query']",
    "input[aria-label*='Search' i]",
)


@dataclass
class Probe:
    name: str
    url: str
    # Optional CSS/text selector to wait for before sampling page content.
    # Leave None to use `networkidle`.
    wait_for: str | None = None
    # Force-fail on these terms appearing (e.g. captcha, "no results found").
    negative_terms: tuple[str, ...] = ()
    # Per-probe override of the default match terms.
    match_terms: tuple[str, ...] = MATCH_TERMS
    # Some directories block headless / unknown UAs. Set True to use a longer timeout.
    slow: bool = False
    # If set, navigate to `url` (no query string), then type this term into a
    # search input and press Enter. Use for SPAs that ignore `?q=` URL params.
    search_query: str | None = None
    # Override search input selectors when the defaults miss.
    search_locators: tuple[str, ...] = DEFAULT_SEARCH_LOCATORS


@dataclass
class Result:
    name: str
    url: str
    status: Status
    matched_term: str | None = None
    error: str | None = None
    snippet: str | None = None
    screenshot: str | None = None
    duration_ms: int = 0
    extras: dict[str, str] = field(default_factory=dict)


PROBES: tuple[Probe, ...] = (
    # URL-query directories (their `?q=` filters server-side or via SPA router)
    Probe(
        "SkillsMP",
        "https://skillsmp.com/?q=backblaze",
        negative_terms=("No skills found",),
    ),
    Probe(
        "SkillsLLM",
        "https://skillsllm.com/?q=backblaze",
        negative_terms=("No results", "Nothing found"),
    ),
    Probe(
        "LobeHub Skills",
        "https://lobehub.com/skills?q=backblaze",
        negative_terms=("No skills found",),
    ),
    Probe(
        "Pawgrammer Skills Market",
        "https://skills.pawgrammer.com/?q=backblaze",
        negative_terms=("No skills found", "couldn't find any skills"),
    ),
    # Interactive-search directories (homepage `?q=` is ignored; type into search box)
    # Claude Marketplaces homepage has no free-text search input — only category
    # browsing and email subscribe forms. Best signal we can get without a known
    # canonical URL is checking if `b2-cloud-storage` appears anywhere on the
    # rendered listings page.
    Probe(
        "Claude Marketplaces",
        "https://claudemarketplaces.com/",
        negative_terms=("No marketplaces found", "0 results"),
    ),
    # ClaudeSkills.info /skills exposes no input element. Their homepage may
    # have a header search; try that instead.
    Probe(
        "ClaudeSkills.info",
        "https://claudeskills.info/",
        search_query="backblaze",
        slow=True,
        negative_terms=("No skills found",),
    ),
    Probe(
        "Agent Skills Market",
        "https://www.agentskillsmarket.space/",
        search_query="backblaze",
        negative_terms=("No skills found", "0 results"),
    ),
    Probe(
        "SkillHub",
        "https://skillhub.club/",
        search_query="backblaze",
        # Their search input is `type='text'` with placeholder "Search Skills..." —
        # the generic locators miss the no-`type=search` case, so list it explicitly.
        search_locators=(
            "input[placeholder='Search Skills...' i]",
            "input[placeholder*='Search Skills' i]",
            *DEFAULT_SEARCH_LOCATORS,
        ),
        negative_terms=("No results", "No skills"),
    ),
    # Direct text probe — no UI involved
    Probe(
        "Awesome Claude Skills",
        "https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "Awesome Claude Plugins",
        "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-claude-plugins/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "Awesome Agent Skills",
        "https://raw.githubusercontent.com/heilcheng/awesome-agent-skills/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    # Anthropic's official directories
    Probe(
        "Anthropic claude-plugins-official",
        "https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage", "backblaze"),
    ),
    Probe(
        "Anthropic skills",
        "https://raw.githubusercontent.com/anthropics/skills/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage", "backblaze"),
    ),
    Probe(
        "claude.com Skills",
        "https://claude.com/skills?q=backblaze",
        slow=True,
        negative_terms=("No skills found", "0 results"),
    ),
    # WordPress-style search (?s=)
    Probe(
        "Cult of Claude",
        "https://cultofclaude.com/skills/?s=backblaze",
        negative_terms=("Nothing Found", "Sorry, but nothing matched"),
    ),
    # Community marketplaces — also crawl GitHub topics
    Probe(
        "alirezarezvani/claude-skills",
        "https://raw.githubusercontent.com/alirezarezvani/claude-skills/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "daymade/claude-code-skills",
        "https://raw.githubusercontent.com/daymade/claude-code-skills/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "mhattingpete/claude-skills-marketplace",
        "https://raw.githubusercontent.com/mhattingpete/claude-skills-marketplace/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    # Tier-1 aggregators added 2026-05. Raw README grep — no JS needed but kept
    # here for parity with the rest of the directory list and one-stop reporting.
    Probe(
        "VoltAgent/awesome-agent-skills",
        "https://raw.githubusercontent.com/VoltAgent/awesome-agent-skills/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "hesreallyhim/awesome-claude-code",
        "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "ComposioHQ/awesome-claude-skills",
        # Default branch is `master`, not `main`.
        "https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "netresearch/claude-code-marketplace",
        # The manifest is the authoritative listing; README may lag.
        "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/.claude-plugin/marketplace.json",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage", "b2-cloud-storage"),
    ),
    # Tier-2 community lists
    Probe(
        "rohitg00/awesome-claude-code-toolkit",
        "https://raw.githubusercontent.com/rohitg00/awesome-claude-code-toolkit/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "BehiSecc/awesome-claude-skills",
        "https://raw.githubusercontent.com/BehiSecc/awesome-claude-skills/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    Probe(
        "jqueryscript/awesome-claude-code",
        "https://raw.githubusercontent.com/jqueryscript/awesome-claude-code/main/README.md",
        match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
    ),
    # SPA aggregators — must use Playwright (mcpmarket 403s plain curl, awesomeclaude
    # is a Next.js site that hydrates client-side).
    Probe(
        "MCP Market — Skills",
        "https://mcpmarket.com/tools/skills?q=backblaze",
        slow=True,
        negative_terms=("No skills found", "No results", "0 results"),
    ),
    Probe(
        "awesomeclaude.ai",
        "https://awesomeclaude.ai/awesome-claude-skills",
        search_query="backblaze",
        slow=True,
        negative_terms=("No skills found", "No results"),
    ),
)


def _snippet_around(text: str, term: str, span: int = 80) -> str:
    """Return ~`span` chars of context around the first occurrence of `term`."""
    idx = text.lower().find(term.lower())
    if idx < 0:
        return ""
    start = max(0, idx - span)
    end = min(len(text), idx + len(term) + span)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _check_page_text(text: str, probe: Probe) -> tuple[Status, str | None, str | None]:
    """Return (status, matched_term, snippet) for the rendered text."""
    haystack = text.lower()
    for neg in probe.negative_terms:
        if neg.lower() in haystack:
            return "not_found", None, _snippet_around(text, neg)
    for term in probe.match_terms:
        if term.lower() in haystack:
            return "live", term, _snippet_around(text, term)
    return "not_found", None, None


def _dismiss_overlays(page: Page) -> None:
    """Best-effort: close common modals/banners that block search input."""
    # Two Escape presses — some modals require it; one to defocus, one to close.
    for _ in range(2):
        try:
            page.keyboard.press("Escape", timeout=500)
            page.wait_for_timeout(150)
        except Exception:
            pass
    candidates = (
        'button[aria-label="Dismiss"]',
        'button[aria-label="Close"]',
        '[aria-label*="close" i]',
        '[aria-label*="dismiss" i]',
        'button:has-text("Got it")',
        'button:has-text("Accept")',
        'button:has-text("Dismiss")',
        'button:has-text("Close")',
    )
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if loc.is_visible(timeout=400):
                # force=True bypasses overlay-intercepts; clicking through is what we want.
                loc.click(timeout=1500, force=True)
                page.wait_for_timeout(250)
        except Exception:
            continue


def _interactive_search(page: Page, probe: Probe) -> str | None:
    """Find a search input, type the query, press Enter. Returns the locator
    that worked (for debugging) or None if all candidates failed."""
    if not probe.search_query:
        return None
    _dismiss_overlays(page)
    for sel in probe.search_locators:
        try:
            loc = page.locator(sel).first
            if not loc.is_visible(timeout=1500):
                continue
            loc.fill(probe.search_query, timeout=2000)
            loc.press("Enter", timeout=2000)
            with contextlib.suppress(PlaywrightTimeout):
                page.wait_for_load_state("networkidle", timeout=10_000)
            # Some search UIs debounce — give the DOM another moment.
            page.wait_for_timeout(800)
            return sel
        except Exception:
            continue
    return None


def run_probe(page: Page, probe: Probe, save_screenshots: bool) -> Result:
    started = datetime.now(timezone.utc)
    result = Result(name=probe.name, url=probe.url, status="error")
    try:
        timeout = 60_000 if probe.slow else 30_000
        response = page.goto(probe.url, wait_until="domcontentloaded", timeout=timeout)
        if response is None:
            result.error = "no response"
            return result
        elif response.status >= 400:
            result.status = "blocked" if response.status in (401, 403, 429) else "error"
            result.error = f"HTTP {response.status}"
            return result

        # Best-effort: let SPAs settle. Don't fail if networkidle never resolves.
        with contextlib.suppress(PlaywrightTimeout):
            page.wait_for_load_state("networkidle", timeout=15_000)

        if probe.wait_for:
            with contextlib.suppress(PlaywrightTimeout):
                page.wait_for_selector(probe.wait_for, timeout=10_000)

        # Interactive search if configured (homepage doesn't honor ?q=).
        if probe.search_query:
            used = _interactive_search(page, probe)
            result.extras["search_locator"] = used or "<none-matched>"

        # Pull rendered text. `inner_text("body")` reflects what a user sees,
        # ignoring HTML attributes / JSON blobs.
        try:
            text = page.inner_text("body")
        except PlaywrightTimeout:
            text = page.content()  # fall back to raw HTML for raw.githubusercontent.com etc.

        status, matched, snippet = _check_page_text(text, probe)
        result.status = status
        result.matched_term = matched
        result.snippet = snippet

    except PlaywrightTimeout as exc:
        result.error = f"timeout: {exc}"
    except Exception as exc:
        result.error = f"{type(exc).__name__}: {exc}"
    finally:
        if save_screenshots and probe.url.startswith("http") and result.status != "error":
            SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            path = SCREENSHOT_DIR / f"{probe.name.replace(' ', '_')}.png"
            try:
                page.screenshot(path=str(path), full_page=True)
                result.screenshot = str(path.relative_to(REPO_ROOT))
            except Exception:
                pass
        result.duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
    return result


def render_markdown(results: list[Result]) -> str:
    icon = {"live": "✅", "not_found": "❌", "error": "⚠️", "blocked": "🔒"}
    lines = [
        f"# Listing status — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Repo: `{REPO_SLUG}`  •  Skill: `{SKILL_NAME}`",
        "",
        "| Directory | Status | Matched | Detail |",
        "|---|---|---|---|",
    ]
    for r in results:
        detail = r.error or r.snippet or ""
        if len(detail) > 90:
            detail = detail[:87] + "…"
        lines.append(
            f"| {r.name} | {icon.get(r.status, '?')} {r.status} "
            f"| {r.matched_term or '—'} | {detail} |"
        )
    live = sum(1 for r in results if r.status == "live")
    lines += ["", f"**{live}/{len(results)} live.**"]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--headed", action="store_true", help="Show browser window")
    parser.add_argument("--only", action="append", help="Restrict to one directory (repeatable)")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of markdown")
    parser.add_argument(
        "--screenshots",
        action="store_true",
        help="Save full-page screenshots to dist/listing-checks/",
    )
    parser.add_argument(
        "--user-agent",
        default=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        ),
    )
    args = parser.parse_args()

    probes: list[Probe] = list(PROBES)
    if args.only:
        wanted = {n.lower() for n in args.only}
        probes = [p for p in probes if p.name.lower() in wanted]
        if not probes:
            print(f"No matching probes for --only {args.only}", file=sys.stderr)
            return 2

    results: list[Result] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            user_agent=args.user_agent, viewport={"width": 1366, "height": 900}
        )
        page = context.new_page()
        for probe in probes:
            print(f"  → {probe.name}  …  ", end="", flush=True, file=sys.stderr)
            r = run_probe(page, probe, save_screenshots=args.screenshots)
            results.append(r)
            tag = r.matched_term or r.error or "—"
            print(f"{r.status}  ({r.duration_ms}ms)  {tag}", file=sys.stderr)
        context.close()
        browser.close()

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        print(render_markdown(results))
    return 0 if all(r.status in ("live", "not_found") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
