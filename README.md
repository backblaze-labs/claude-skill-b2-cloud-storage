# Claude Skill: Backblaze B2 Cloud Storage Manager

[![CI](https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/actions/workflows/ci.yml/badge.svg)](https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE.txt)
[![Python 3.10–3.14](https://img.shields.io/badge/python-3.10%E2%80%933.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white)](https://github.com/pre-commit/pre-commit)
[![Spell-checked: cspell](https://img.shields.io/badge/spell--check-cspell-blue)](https://cspell.org/)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-compatible-8B5CF6?logo=anthropic&logoColor=white)](https://claude.ai/code)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-spec-FF6B35)](https://agentskills.io)
[![Backblaze B2](https://img.shields.io/badge/Backblaze-B2-E8231A?logo=backblaze&logoColor=white)](https://www.backblaze.com/cloud-storage)
[![GitHub stars](https://img.shields.io/github/stars/backblaze-labs/claude-skill-b2-cloud-storage?style=flat&logo=github)](https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/stargazers)

A [Claude Code](https://claude.ai/code) skill for managing [Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=claudeskill) cloud storage directly from your terminal — list files, audit buckets, clean up stale data, and review security posture.

Built on the open [Agent Skills](https://agentskills.io) specification. Compatible with Claude Code, Codex CLI, Cursor, Gemini CLI, and other skills-compatible agents.

<details>
<summary>What each badge means</summary>

| Badge | Meaning |
|---|---|
| **CI** | GitHub Actions runs lint, tests, frontmatter validation, and pre-commit on every PR across Python 3.10–3.14. |
| **License: MIT** | Permissive open-source license — free to fork, modify, and ship. |
| **Python 3.10–3.14** | Tested on every currently-supported CPython version. Python 3.9 reached EOL in October 2025 and is no longer in the matrix. |
| **Ruff** | Linted and formatted with [Astral's Ruff](https://github.com/astral-sh/ruff). Enforced via pre-commit. |
| **Checked with mypy** | Static type-checked. The audit script's public surface and the B2 JSON inputs are fully annotated. |
| **pre-commit** | Hooks for whitespace, JSON/YAML validity, ruff, markdownlint, yamllint, cspell, and mypy run on every commit. |
| **Spell-checked: cspell** | Markdown and Python prose are spell-checked with a project-specific allowlist. |
| **Claude Code** | First-class compatibility with [Claude Code](https://claude.ai/code) — auto-invoked when you mention B2 in chat. |
| **Agent Skills** | Conforms to the open [Agent Skills](https://agentskills.io) `SKILL.md` specification — works in any compatible agent (Codex CLI, Cursor, Gemini CLI, etc.). |
| **Backblaze B2** | Targets the [Backblaze B2 Cloud Storage](https://www.backblaze.com/cloud-storage) platform via the official `b2` CLI v4+. |
| **GitHub stars** | Community signal — give it a ⭐ if it's useful. |

</details>

## Features

- **List & search** objects across buckets with prefix filtering
- **Storage audit** — live vs. billable storage, breakdown by prefix + extension, configurable thresholds
- **Hidden-cost detection** — surfaces unfinished large uploads, old versions, and hide markers that still bill
- **Cost estimation** — monthly storage cost + potential savings after cleanup
- **Duplicate detection** — groups files by `contentSha1` (true duplicates, not same-name)
- **Stale & large-file flags** — configurable `--stale-days` and `--large-mb` thresholds
- **JSON output** — `--json` flag for downstream analysis
- **Cleanup with safety** — mandatory dry-run + explicit "yes" confirmation before any deletion
- **Security review** — per-bucket checklist (type, SSE, CORS, object lock, replication, lifecycle coverage)
- **Lifecycle rules** — view and update expiration policies
- **Guided setup** — walks through CLI install, app-key creation, and authorization
- **Per-project config** — different buckets and credentials per project

## Install

Pick whichever fits your tooling. All methods install the same skill folder; only the delivery differs.

### 1. `npx skills add` — open spec CLI (recommended cross-agent)

Works with any [Agent Skills](https://agentskills.io)-compatible client (Claude Code, Codex CLI, Cursor, Gemini CLI, Goose, OpenCode, etc.).

```bash
npx skills add backblaze-labs/claude-skill-b2-cloud-storage -g    # global
npx skills add backblaze-labs/claude-skill-b2-cloud-storage       # current project only
```

The `-g` flag installs system-wide (`~/.claude/skills/` for Claude Code). Without it, the skill is scoped to the current project.

### 2. Claude Code plugin marketplace (recommended for Claude Code users)

Inside Claude Code:

```text
/plugin marketplace add backblaze-labs/claude-skill-b2-cloud-storage
/plugin install b2-cloud-storage
```

This reads the `.claude-plugin/marketplace.json` in the repo and installs the skill plus any future plugins shipped from the same source.

### 3. GitHub Release tarball

**Latest** (always points at the most recent release):

```bash
curl -L https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/releases/latest/download/b2-cloud-storage.tar.gz \
  | tar xz -C ~/.claude/skills/
```

**Pinned to a specific version** (deterministic deploys, air-gapped environments):

```bash
# Substitute the tag you want — see https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/releases
TAG=vX.Y.Z
curl -L "https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/releases/download/${TAG}/b2-cloud-storage-${TAG}.tar.gz" \
  | tar xz -C ~/.claude/skills/
```

Each release ships four artifacts: an unversioned `b2-cloud-storage.tar.gz` / `.zip` (used by the latest URL) and a `-<tag>` versioned pair for pinning.

### 4. Manual git clone

When you want to edit the skill in place or test changes locally:

```bash
git clone https://github.com/backblaze-labs/claude-skill-b2-cloud-storage.git /tmp/b2-skill \
  && cp -r /tmp/b2-skill/b2-cloud-storage ~/.claude/skills/b2-cloud-storage \
  && rm -rf /tmp/b2-skill
```

Or, if you've already cloned the repo, from the repo root:

```bash
cp -r b2-cloud-storage ~/.claude/skills/b2-cloud-storage
```

### 5. Marketplace-specific CLIs

Once the skill is listed on the respective directory:

```bash
npx @skill-hub/cli install b2-cloud-storage      # SkillHub
lhm install b2-cloud-storage                     # LobeHub (lobehub-cli)
```

See [RELEASE.md](RELEASE.md) for the full list of directories and their listing status.

### Verify

```bash
ls ~/.claude/skills/b2-cloud-storage/SKILL.md
```

Then in Claude Code, restart the session and try `> audit my-bucket for stale files` — the skill is auto-invoked when you mention B2 in natural language.

## Usage

The skill is auto-invoked when you mention B2 in natural language, or you can call it explicitly with `/b2-cloud-storage`:

```text
> help me set up B2

> list everything in my-bucket

> audit my-bucket for stale files, duplicates, and unfinished uploads

> clean up files older than 90 days in my-bucket/logs

> run a security review on my public buckets
```

The audit script can also be run directly:

```bash
python ~/.claude/skills/b2-cloud-storage/scripts/storage_audit.py <bucket>
python ~/.claude/skills/b2-cloud-storage/scripts/storage_audit.py <bucket> --json
python ~/.claude/skills/b2-cloud-storage/scripts/storage_audit.py <bucket> \
  --stale-days 180 --large-mb 500 --prefix-depth 2
```

**Note**: You may need to restart Claude Code after installing the skill for it to be recognized.

## Setup & API Keys

The skill handles setup automatically on first use:

1. **Installs B2 CLI** if not found (`pip install b2`)
2. **Checks authorization** — skips ahead if already configured
3. **Guides API key creation**:
   - Log in at [secure.backblaze.com](https://secure.backblaze.com/app_keys.htm)
   - Go to **App Keys** > **Add a New Application Key**
   - Set permissions (`listBuckets`, `listFiles`, `readFiles` for read-only)
   - Copy the `keyID` and `applicationKey`
4. **Authorizes the CLI** — runs `b2 account authorize` interactively (keys stay in your terminal, never in chat)
5. **Verifies** access with `b2 ls`

Credentials are stored by the B2 CLI in `~/.b2_account_info`. The skill never sees or stores your keys.

## Per-Project Configuration

Different projects can use different B2 buckets and credentials. On first use in a project, the skill asks which bucket to use and saves a config file at `.claude/b2-config.json` in your project root:

```json
{
  "bucket": "my-project-bucket",
  "prefix": "",
  "accountInfoPath": "~/.b2_account_info"
}
```

| Field | Purpose |
|-------|---------|
| `bucket` | Default bucket for this project |
| `prefix` | Scope all operations to a prefix (e.g. `data/models/`) |
| `accountInfoPath` | Path to B2 credential file — use different keys per project |

To use separate credentials per project, authorize into a project-specific file:

```bash
B2_ACCOUNT_INFO=~/.b2_account_info_myproject b2 account authorize
```

Then set `accountInfoPath` to `~/.b2_account_info_myproject` in your project's config.

An example config file is included at [`b2-cloud-storage/b2-config.example.json`](b2-cloud-storage/b2-config.example.json).

**Note**: This config file stores bucket names and file paths only — never API keys or secrets. Add `.claude/b2-config.json` to your `.gitignore`.

## Security

- `b2 account get` and `b2 key *` commands are blocked (credential exposure)
- All deletions require `--dry-run` preview + explicit "yes" confirmation
- Bucket visibility changes (`allPublic`) require warning + confirmation
- All operations default to read-only
- API keys are never stored or displayed by the skill
- If you accidentally paste keys into chat, the skill warns you to rotate them

## File Structure

```text
claude-skill-b2-cloud-storage/
├── README.md
├── .github/workflows/ci.yml             # Lint + tests + frontmatter validation
├── tests/                               # Unit tests for the audit script
└── b2-cloud-storage/                    # Copy this folder to ~/.claude/skills/
    ├── SKILL.md                         # Skill definition and instructions
    ├── b2-config.example.json           # Example per-project config
    ├── scripts/
    │   └── storage_audit.py             # Audit: usage, versions, unfinished, cost
    └── references/
        ├── setup.md                     # First-use setup walk-through
        ├── cleanup-playbook.md          # Safe deletion procedure
        ├── security-review.md           # Per-bucket security checklist
        └── b2-cli-reference.md          # B2 CLI v4 command reference
```

## Requirements

- [Claude Code](https://claude.ai/code) (or any Agent Skills-compatible tool)
- Python 3.10+ (CI tests against 3.10 – 3.14)
- B2 CLI v4+ (auto-installed by the skill)
- A [Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=claudeskill) account

## License

MIT
