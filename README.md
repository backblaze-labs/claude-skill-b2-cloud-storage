# Claude Skill: Backblaze B2 Cloud Storage Manager

A [Claude Code](https://claude.ai/code) skill for managing [Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=claudeskill) cloud storage directly from your terminal — list files, audit buckets, clean up stale data, and review security posture.

Built on the open [Agent Skills](https://agentskills.io) specification. Compatible with Claude Code, Codex CLI, Cursor, Gemini CLI, and other skills-compatible agents.

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

### One-liner

```bash
git clone https://github.com/backblaze-labs/claude-skill-b2-cloud-storage.git /tmp/b2-skill && cp -r /tmp/b2-skill/b2-cloud-storage ~/.claude/skills/b2-cloud-storage && rm -rf /tmp/b2-skill
```

### Manual

```bash
cp -r b2-cloud-storage ~/.claude/skills/b2-cloud-storage
```

### Verify

```bash
ls ~/.claude/skills/b2-cloud-storage/SKILL.md
```

## Usage

The skill is auto-invoked when you mention B2 in natural language, or you can call it explicitly with `/b2-cloud-storage`:

```
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

```
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
- Python 3.9+
- B2 CLI v4+ (auto-installed by the skill)
- A [Backblaze B2](https://www.backblaze.com/cloud-storage?utm_source=github&utm_medium=referral&utm_campaign=ai_artifacts&utm_content=claudeskill) account

## License

MIT
