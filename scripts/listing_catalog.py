"""Canonical marketplace probe definitions shared by the listing checkers."""

from __future__ import annotations

from dataclasses import dataclass

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


MARKETPLACE_PROBES: tuple[MarketplaceProbe, ...] = (
    MarketplaceProbe(
        key="skillsmp",
        http=HttpProbeSpec("SkillsMP (HTML)", "https://skillsmp.com/?q=backblaze"),
        browser=BrowserProbeSpec(
            "SkillsMP",
            "https://skillsmp.com/?q=backblaze",
            negative_terms=("No skills found",),
        ),
    ),
    MarketplaceProbe(
        key="skillsllm",
        browser=BrowserProbeSpec(
            "SkillsLLM",
            "https://skillsllm.com/?q=backblaze",
            negative_terms=("No results", "Nothing found"),
        ),
    ),
    MarketplaceProbe(
        key="lobehub-skills",
        http=HttpProbeSpec("LobeHub Skills (HTML)", "https://lobehub.com/skills?q=backblaze"),
        browser=BrowserProbeSpec(
            "LobeHub Skills",
            "https://lobehub.com/skills?q=backblaze",
            negative_terms=("No skills found",),
        ),
    ),
    MarketplaceProbe(
        key="pawgrammer-skills-market",
        browser=BrowserProbeSpec(
            "Pawgrammer Skills Market",
            "https://skills.pawgrammer.com/?q=backblaze",
            negative_terms=("No skills found", "couldn't find any skills"),
        ),
    ),
    MarketplaceProbe(
        key="claude-marketplaces",
        http=HttpProbeSpec("Claude Marketplaces (HTML)", "https://claudemarketplaces.com/"),
        browser=BrowserProbeSpec(
            "Claude Marketplaces",
            "https://claudemarketplaces.com/",
            negative_terms=("No marketplaces found", "0 results"),
        ),
    ),
    MarketplaceProbe(
        key="claudeskills-info",
        browser=BrowserProbeSpec(
            "ClaudeSkills.info",
            "https://claudeskills.info/",
            search_query="backblaze",
            slow=True,
            negative_terms=("No skills found",),
        ),
    ),
    MarketplaceProbe(
        key="agent-skills-market",
        browser=BrowserProbeSpec(
            "Agent Skills Market",
            "https://www.agentskillsmarket.space/",
            search_query="backblaze",
            negative_terms=("No skills found", "0 results"),
        ),
    ),
    MarketplaceProbe(
        key="skillhub",
        browser=BrowserProbeSpec(
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
    ),
    MarketplaceProbe(
        key="awesome-claude-skills-travisvn",
        http=HttpProbeSpec(
            "Awesome Claude Skills (travisvn)",
            "https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "Awesome Claude Skills",
            "https://raw.githubusercontent.com/travisvn/awesome-claude-skills/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="awesome-claude-plugins-chat2anyllm",
        http=HttpProbeSpec(
            "Awesome Claude Plugins (Chat2AnyLLM)",
            "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-claude-plugins/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "Awesome Claude Plugins",
            "https://raw.githubusercontent.com/Chat2AnyLLM/awesome-claude-plugins/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="awesome-agent-skills-heilcheng",
        http=HttpProbeSpec(
            "Awesome Agent Skills (heilcheng)",
            "https://raw.githubusercontent.com/heilcheng/awesome-agent-skills/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "Awesome Agent Skills",
            "https://raw.githubusercontent.com/heilcheng/awesome-agent-skills/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="anthropic-claude-plugins-official",
        http=HttpProbeSpec(
            "Anthropic claude-plugins-official",
            "https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "Anthropic claude-plugins-official",
            "https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage", "backblaze"),
        ),
    ),
    MarketplaceProbe(
        key="anthropic-skills",
        http=HttpProbeSpec(
            "Anthropic skills",
            "https://raw.githubusercontent.com/anthropics/skills/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "Anthropic skills",
            "https://raw.githubusercontent.com/anthropics/skills/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage", "backblaze"),
        ),
    ),
    MarketplaceProbe(
        key="claude-com-skills",
        browser=BrowserProbeSpec(
            "claude.com Skills",
            "https://claude.com/skills?q=backblaze",
            slow=True,
            negative_terms=("No skills found", "0 results"),
        ),
    ),
    MarketplaceProbe(
        key="cult-of-claude",
        http=HttpProbeSpec("Cult of Claude (HTML)", "https://cultofclaude.com/skills/?s=backblaze"),
        browser=BrowserProbeSpec(
            "Cult of Claude",
            "https://cultofclaude.com/skills/?s=backblaze",
            negative_terms=("Nothing Found", "Sorry, but nothing matched"),
        ),
    ),
    MarketplaceProbe(
        key="alirezarezvani-claude-skills",
        http=HttpProbeSpec(
            "alirezarezvani/claude-skills",
            "https://raw.githubusercontent.com/alirezarezvani/claude-skills/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "alirezarezvani/claude-skills",
            "https://raw.githubusercontent.com/alirezarezvani/claude-skills/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="daymade-claude-code-skills",
        http=HttpProbeSpec(
            "daymade/claude-code-skills",
            "https://raw.githubusercontent.com/daymade/claude-code-skills/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "daymade/claude-code-skills",
            "https://raw.githubusercontent.com/daymade/claude-code-skills/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="mhattingpete-claude-skills-marketplace",
        http=HttpProbeSpec(
            "mhattingpete/claude-skills-marketplace",
            "https://raw.githubusercontent.com/mhattingpete/claude-skills-marketplace/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "mhattingpete/claude-skills-marketplace",
            "https://raw.githubusercontent.com/mhattingpete/claude-skills-marketplace/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="voltagent-awesome-agent-skills",
        http=HttpProbeSpec(
            "VoltAgent/awesome-agent-skills",
            "https://raw.githubusercontent.com/VoltAgent/awesome-agent-skills/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "VoltAgent/awesome-agent-skills",
            "https://raw.githubusercontent.com/VoltAgent/awesome-agent-skills/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="hesreallyhim-awesome-claude-code",
        http=HttpProbeSpec(
            "hesreallyhim/awesome-claude-code",
            "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "hesreallyhim/awesome-claude-code",
            "https://raw.githubusercontent.com/hesreallyhim/awesome-claude-code/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="composiohq-awesome-claude-skills",
        http=HttpProbeSpec(
            "ComposioHQ/awesome-claude-skills",
            "https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/README.md",
        ),
        browser=BrowserProbeSpec(
            "ComposioHQ/awesome-claude-skills",
            "https://raw.githubusercontent.com/ComposioHQ/awesome-claude-skills/master/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="netresearch-claude-code-marketplace-readme",
        http=HttpProbeSpec(
            "netresearch/claude-code-marketplace (README)",
            "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/README.md",
        ),
    ),
    MarketplaceProbe(
        key="netresearch-claude-code-marketplace-manifest",
        http=HttpProbeSpec(
            "netresearch/claude-code-marketplace (manifest)",
            "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/.claude-plugin/marketplace.json",
        ),
        browser=BrowserProbeSpec(
            "netresearch/claude-code-marketplace",
            "https://raw.githubusercontent.com/netresearch/claude-code-marketplace/main/.claude-plugin/marketplace.json",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage", "b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="rohitg00-awesome-claude-code-toolkit",
        http=HttpProbeSpec(
            "rohitg00/awesome-claude-code-toolkit",
            "https://raw.githubusercontent.com/rohitg00/awesome-claude-code-toolkit/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "rohitg00/awesome-claude-code-toolkit",
            "https://raw.githubusercontent.com/rohitg00/awesome-claude-code-toolkit/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="behisecc-awesome-claude-skills",
        http=HttpProbeSpec(
            "BehiSecc/awesome-claude-skills",
            "https://raw.githubusercontent.com/BehiSecc/awesome-claude-skills/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "BehiSecc/awesome-claude-skills",
            "https://raw.githubusercontent.com/BehiSecc/awesome-claude-skills/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="jqueryscript-awesome-claude-code",
        http=HttpProbeSpec(
            "jqueryscript/awesome-claude-code",
            "https://raw.githubusercontent.com/jqueryscript/awesome-claude-code/main/README.md",
        ),
        browser=BrowserProbeSpec(
            "jqueryscript/awesome-claude-code",
            "https://raw.githubusercontent.com/jqueryscript/awesome-claude-code/main/README.md",
            match_terms=(REPO_SLUG, "claude-skill-b2-cloud-storage"),
        ),
    ),
    MarketplaceProbe(
        key="mcp-market-skills",
        browser=BrowserProbeSpec(
            "MCP Market — Skills",
            "https://mcpmarket.com/tools/skills?q=backblaze",
            slow=True,
            negative_terms=("No skills found", "No results", "0 results"),
        ),
    ),
    MarketplaceProbe(
        key="awesomeclaude-ai",
        browser=BrowserProbeSpec(
            "awesomeclaude.ai",
            "https://awesomeclaude.ai/awesome-claude-skills",
            search_query="backblaze",
            slow=True,
            negative_terms=("No skills found", "No results"),
        ),
    ),
)

HTTP_PROBES: tuple[HttpProbeSpec, ...] = tuple(
    probe.http for probe in MARKETPLACE_PROBES if probe.http is not None
)

BROWSER_PROBES: tuple[BrowserProbeSpec, ...] = tuple(
    probe.browser for probe in MARKETPLACE_PROBES if probe.browser is not None
)
