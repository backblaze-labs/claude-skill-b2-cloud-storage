"""Canonical marketplace probe definitions shared by the listing checkers."""

from __future__ import annotations

from dataclasses import dataclass

# Public surface consumed by the sibling checkers (check_listings*.py) and tests.
# HTTP_PROBES / BROWSER_PROBES look unused within this module, but are imported
# elsewhere; listing them here documents the export and satisfies that analysis.
__all__ = [
    "BROWSER_PROBES",
    "HTTP_PROBES",
    "REPO_SLUG",
    "SKILL_NAME",
    "BrowserProbeSpec",
    "HttpProbeSpec",
]

REPO_SLUG = "backblaze-labs/claude-skill-b2-cloud-storage"
SKILL_NAME = "b2-cloud-storage"

HTTP_MATCH_TERMS = (
    REPO_SLUG.lower(),
    "claude-skill-b2-cloud-storage",
)

BROWSER_MATCH_TERMS = (
    "backblaze-labs/claude-skill-b2-cloud-storage",
    "claude-skill-b2-cloud-storage",
    "b2-cloud-storage",
)

DEFAULT_SEARCH_LOCATORS = (
    "input[type='search']",
    "[role='searchbox']",
    "input[placeholder*='Search' i]",
    "input[name='q']",
    "input[name='query']",
    "input[aria-label*='Search' i]",
)


@dataclass(frozen=True)
class HttpProbeSpec:
    name: str
    url: str
    match_terms: tuple[str, ...] = HTTP_MATCH_TERMS


@dataclass(frozen=True)
class BrowserProbeSpec:
    name: str
    url: str
    wait_for: str | None = None
    negative_terms: tuple[str, ...] = ()
    match_terms: tuple[str, ...] = BROWSER_MATCH_TERMS
    slow: bool = False
    search_query: str | None = None
    search_locators: tuple[str, ...] = DEFAULT_SEARCH_LOCATORS


@dataclass(frozen=True)
class MarketplaceProbe:
    key: str
    http: HttpProbeSpec | None = None
    browser: BrowserProbeSpec | None = None


RAW_MATCH_TERMS = (REPO_SLUG, "claude-skill-b2-cloud-storage")


def http_only(
    key: str,
    name: str,
    url: str,
    *,
    match_terms: tuple[str, ...] = HTTP_MATCH_TERMS,
) -> MarketplaceProbe:
    return MarketplaceProbe(key=key, http=HttpProbeSpec(name, url, match_terms=match_terms))


def browser_only(
    key: str,
    name: str,
    url: str,
    *,
    wait_for: str | None = None,
    negative_terms: tuple[str, ...] = (),
    match_terms: tuple[str, ...] = BROWSER_MATCH_TERMS,
    slow: bool = False,
    search_query: str | None = None,
    search_locators: tuple[str, ...] = DEFAULT_SEARCH_LOCATORS,
) -> MarketplaceProbe:
    return MarketplaceProbe(
        key=key,
        browser=BrowserProbeSpec(
            name,
            url,
            wait_for=wait_for,
            negative_terms=negative_terms,
            match_terms=match_terms,
            slow=slow,
            search_query=search_query,
            search_locators=search_locators,
        ),
    )


def shared_probe(
    key: str,
    name: str,
    url: str,
    *,
    http_name: str | None = None,
    browser_name: str | None = None,
    http_match_terms: tuple[str, ...] = HTTP_MATCH_TERMS,
    browser_match_terms: tuple[str, ...] = BROWSER_MATCH_TERMS,
    wait_for: str | None = None,
    negative_terms: tuple[str, ...] = (),
    slow: bool = False,
    search_query: str | None = None,
    search_locators: tuple[str, ...] = DEFAULT_SEARCH_LOCATORS,
) -> MarketplaceProbe:
    return MarketplaceProbe(
        key=key,
        http=HttpProbeSpec(http_name or name, url, match_terms=http_match_terms),
        browser=BrowserProbeSpec(
            browser_name or name,
            url,
            wait_for=wait_for,
            negative_terms=negative_terms,
            match_terms=browser_match_terms,
            slow=slow,
            search_query=search_query,
            search_locators=search_locators,
        ),
    )


MARKETPLACE_PROBES: tuple[MarketplaceProbe, ...] = (
    shared_probe(
        "skillsmp",
        "SkillsMP",
        "https://skillsmp.com/?q=backblaze",
        http_name="SkillsMP (HTML)",
        negative_terms=("No skills found",),
    ),
    browser_only(
        "skillsllm",
        "SkillsLLM",
        "https://skillsllm.com/?q=backblaze",
        negative_terms=("No results", "Nothing found"),
    ),
    shared_probe(
        "lobehub-skills",
        "LobeHub Skills",
        "https://lobehub.com/skills?q=backblaze",
        http_name="LobeHub Skills (HTML)",
        negative_terms=("No skills found",),
    ),
    browser_only(
        "pawgrammer-skills-market",
        "Pawgrammer Skills Market",
        "https://skills.pawgrammer.com/?q=backblaze",
        negative_terms=("No skills found", "couldn't find any skills"),
    ),
    shared_probe(
        "claude-marketplaces",
        "Claude Marketplaces",
        "https://claudemarketplaces.com/",
        http_name="Claude Marketplaces (HTML)",
        negative_terms=("No marketplaces found", "0 results"),
    ),
    browser_only(
        "claudeskills-info",
        "ClaudeSkills.info",
        "https://claudeskills.info/",
        search_query="backblaze",
        slow=True,
        negative_terms=("No skills found",),
    ),
    browser_only(
        "agent-skills-market",
        "Agent Skills Market",
        "https://www.agentskillsmarket.space/",
        search_query="backblaze",
        negative_terms=("No skills found", "0 results"),
    ),
    browser_only(
        "skillhub",
        "SkillHub",
        "https://skillhub.club/",
        search_query="backblaze",
        search_locators=(
            "input[placeholder='Search Skills...' i]",
            "input[placeholder*='Search Skills' i]",
            *DEFAULT_SEARCH_LOCATORS,
        ),
        negative_terms=("No results", "No skills"),
    ),
    shared_probe(
        "awesome-claude-skills-travisvn",
        "Awesome Claude Skills",
        "https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md",
        http_name="Awesome Claude Skills (travisvn)",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "awesome-claude-plugins-chat2anyllm",
        "Awesome Claude Plugins",
        "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-claude-plugins/main/README.md",
        http_name="Awesome Claude Plugins (Chat2AnyLLM)",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "awesome-agent-skills-heilcheng",
        "Awesome Agent Skills",
        "https://raw.githubusercontent.com/heilcheng/awesome-agent-skills/main/README.md",
        http_name="Awesome Agent Skills (heilcheng)",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "anthropic-claude-plugins-official",
        "Anthropic claude-plugins-official",
        "https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/README.md",
        browser_match_terms=(*RAW_MATCH_TERMS, "backblaze"),
    ),
    shared_probe(
        "anthropic-skills",
        "Anthropic skills",
        "https://raw.githubusercontent.com/anthropics/skills/main/README.md",
        browser_match_terms=(*RAW_MATCH_TERMS, "backblaze"),
    ),
    browser_only(
        "claude-com-skills",
        "claude.com Skills",
        "https://claude.com/skills?q=backblaze",
        slow=True,
        negative_terms=("No skills found", "0 results"),
    ),
    shared_probe(
        "cult-of-claude",
        "Cult of Claude",
        "https://cultofclaude.com/skills/?s=backblaze",
        http_name="Cult of Claude (HTML)",
        negative_terms=("Nothing Found", "Sorry, but nothing matched"),
    ),
    shared_probe(
        "alirezarezvani-claude-skills",
        "alirezarezvani/claude-skills",
        "https://raw.githubusercontent.com/alirezarezvani/claude-skills/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "daymade-claude-code-skills",
        "daymade/claude-code-skills",
        "https://raw.githubusercontent.com/daymade/claude-code-skills/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "mhattingpete-claude-skills-marketplace",
        "mhattingpete/claude-skills-marketplace",
        "https://raw.githubusercontent.com/mhattingpete/claude-skills-marketplace/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "voltagent-awesome-agent-skills",
        "VoltAgent/awesome-agent-skills",
        "https://raw.githubusercontent.com/VoltAgent/awesome-agent-skills/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "hesreallyhim-awesome-claude-code",
        "hesreallyhim/awesome-claude-code",
        "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "composiohq-awesome-claude-skills",
        "ComposioHQ/awesome-claude-skills",
        "https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    http_only(
        "netresearch-claude-code-marketplace-readme",
        "netresearch/claude-code-marketplace (README)",
        "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/README.md",
    ),
    shared_probe(
        "netresearch-claude-code-marketplace-manifest",
        "netresearch/claude-code-marketplace",
        "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/.claude-plugin/marketplace.json",
        http_name="netresearch/claude-code-marketplace (manifest)",
        browser_match_terms=(*RAW_MATCH_TERMS, "b2-cloud-storage"),
    ),
    shared_probe(
        "rohitg00-awesome-claude-code-toolkit",
        "rohitg00/awesome-claude-code-toolkit",
        "https://raw.githubusercontent.com/rohitg00/awesome-claude-code-toolkit/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "behisecc-awesome-claude-skills",
        "BehiSecc/awesome-claude-skills",
        "https://raw.githubusercontent.com/BehiSecc/awesome-claude-skills/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    shared_probe(
        "jqueryscript-awesome-claude-code",
        "jqueryscript/awesome-claude-code",
        "https://raw.githubusercontent.com/jqueryscript/awesome-claude-code/main/README.md",
        browser_match_terms=RAW_MATCH_TERMS,
    ),
    browser_only(
        "mcp-market-skills",
        "MCP Market — Skills",
        "https://mcpmarket.com/tools/skills?q=backblaze",
        slow=True,
        negative_terms=("No skills found", "No results", "0 results"),
    ),
    browser_only(
        "awesomeclaude-ai",
        "awesomeclaude.ai",
        "https://awesomeclaude.ai/awesome-claude-skills",
        search_query="backblaze",
        slow=True,
        negative_terms=("No skills found", "No results"),
    ),
)

HTTP_PROBES: tuple[HttpProbeSpec, ...] = tuple(
    probe.http for probe in MARKETPLACE_PROBES if probe.http is not None
)

BROWSER_PROBES: tuple[BrowserProbeSpec, ...] = tuple(
    probe.browser for probe in MARKETPLACE_PROBES if probe.browser is not None
)
