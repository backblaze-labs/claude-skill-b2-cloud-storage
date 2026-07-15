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
from typing import Any, Literal

try:
    from playwright.sync_api import Page, sync_playwright
    from playwright.sync_api import TimeoutError as PlaywrightTimeout
except ImportError:  # pragma: no cover
    Page = Any
    PlaywrightTimeout = TimeoutError
    sync_playwright = None

from listing_catalog import BROWSER_PROBES, REPO_SLUG, SKILL_NAME, BrowserProbeSpec

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = REPO_ROOT / "dist" / "listing-checks"

Status = Literal["live", "not_found", "error", "blocked"]


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


PROBES = BROWSER_PROBES


def _snippet_around(text: str, term: str, span: int = 80) -> str:
    """Return ~`span` chars of context around the first occurrence of `term`."""
    idx = text.lower().find(term.lower())
    if idx < 0:
        return ""
    start = max(0, idx - span)
    end = min(len(text), idx + len(term) + span)
    return re.sub(r"\s+", " ", text[start:end]).strip()


def _check_page_text(text: str, probe: BrowserProbeSpec) -> tuple[Status, str | None, str | None]:
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
    # Two Escape presses (defocus, then close); best-effort, so ignore input errors.
    for _ in range(2):
        with contextlib.suppress(Exception):
            page.keyboard.press("Escape", timeout=500)
            page.wait_for_timeout(150)
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


def _interactive_search(page: Page, probe: BrowserProbeSpec) -> str | None:
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


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._")
    return safe or "probe"


def screenshot_path_for_probe(name: str) -> Path:
    return SCREENSHOT_DIR / f"{_safe_filename(name)}.png"


def _normalized_filter(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def filter_probes(
    probes: tuple[BrowserProbeSpec, ...], only: list[str] | None
) -> list[BrowserProbeSpec]:
    if not only:
        return list(probes)
    wanted = {_normalized_filter(name) for name in only}
    return [
        probe
        for probe in probes
        if any(
            want == _normalized_filter(probe.name) or want in _normalized_filter(probe.name)
            for want in wanted
        )
    ]


def run_probe(page: Page, probe: BrowserProbeSpec, save_screenshots: bool) -> Result:
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
            path = screenshot_path_for_probe(probe.name)
            # Screenshots are evidence, not required output; never fail the probe over one.
            with contextlib.suppress(Exception):
                page.screenshot(path=str(path), full_page=True)
                result.screenshot = str(path.relative_to(REPO_ROOT))
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

    probes = filter_probes(PROBES, args.only)
    if not probes:
        print(f"No matching probes for --only {args.only}", file=sys.stderr)
        return 2

    if sync_playwright is None:
        print(
            "playwright is not installed. Run:\n"
            "    pip install playwright && playwright install chromium",
            file=sys.stderr,
        )
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
