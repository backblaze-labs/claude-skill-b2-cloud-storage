---
name: b2-cloud-storage
description: Manage Backblaze B2 cloud storage — list files, audit usage, estimate cost, clean up stale data, review security posture, and manage lifecycle rules. Use when the user mentions B2, Backblaze, object storage buckets, or storage cleanup.
license: MIT
compatibility: Requires b2 CLI v4+ (pip install b2) and Python 3.9+.
metadata:
  author: jdeleon
  version: "1.1"
allowed-tools: Bash(b2:*) Bash(python:*) Bash(pip:*) Bash(pip3:*) Read Write Grep Glob
---

# B2 Cloud Storage Management

Manage Backblaze B2 cloud storage: list files, audit usage, estimate cost, clean up stale data, and review security posture.

## Security Rules (MANDATORY)

1. **Never** run `b2 account get`, `b2 account clear`, or any `b2 key *` subcommand — these expose or mutate credentials.
2. **Never** read `~/.b2_account_info` or any file matching `*b2_account_info*` — this is the B2 credential database (SQLite).
3. **Always** run `b2 rm --dry-run` before any real deletion; show the user what would be deleted and require an explicit "yes" before executing.
4. **Never** change a bucket to `allPublic` without first warning the user about the security implications and getting explicit confirmation.
5. **Default to read-only** — only perform writes or deletes when the user explicitly requests them.
6. **Never** store or write API keys, application keys, or account IDs to any file.
7. If the user pastes key values into the chat instead of the terminal, warn them immediately and recommend rotating the key. Never echo, store, or reference key values that appear in conversation.

## First-Use Flow

1. Check the B2 CLI is installed: `b2 version`. If missing, install (`pip install b2`) — see `references/setup.md` for detail.
2. Verify the CLI is authorized: `b2 ls`. If it fails with an auth error, walk the user through `references/setup.md`.
3. Check for a per-project config at `.claude/b2-config.json` in the project root. If missing, ask the user for bucket + prefix and create one.

### Interactive auth note
`b2 account authorize` (no args) reads keys from an interactive prompt, which agents cannot drive. The user has two options:
- Run it themselves in the terminal — in Claude Code they can type `!b2 account authorize` to execute directly in the session.
- Pass the keyID and applicationKey as positional args: `b2 account authorize <keyID> <appKey>` (keys will appear in shell history — less safe).
- Or set `B2_APPLICATION_KEY_ID` and `B2_APPLICATION_KEY` env vars before running B2 commands (recommended for scripts and CI).

## Project-Level Config

Per-project config at `.claude/b2-config.json`:

```json
{
  "bucket": "my-project-bucket",
  "prefix": "",
  "accountInfoPath": "~/.b2_account_info"
}
```

| Field | Purpose |
|-------|---------|
| `bucket` | Default bucket name for this project |
| `prefix` | Optional prefix to scope all operations (e.g. `data/models/`) |
| `accountInfoPath` | Path to B2 credential file — allows different keys per project |

If `accountInfoPath` differs from the default, prepend `B2_ACCOUNT_INFO=<path>` when running b2 commands. This file stores bucket names and paths only — never API keys.

## Common Actions

### List & search
```bash
b2 ls b2://<bucket>                    # top-level
b2 ls -r b2://<bucket>                 # recursive
b2 ls -r --json b2://<bucket>          # JSON for scripting
b2 ls --versions -r --json b2://<b>    # include old versions + hide markers
b2 ls b2://<bucket>/<prefix>           # prefix-scoped
```

### Inspect file
```bash
b2 file info b2id://<fileId>
```

### Storage audit (usage, stale, large, duplicates, cost)
```bash
python scripts/storage_audit.py <bucket>
python scripts/storage_audit.py <bucket> --json
python scripts/storage_audit.py <bucket> --stale-days 180 --large-mb 500 --prefix-depth 2
```

Reports live vs. billable storage, unfinished large files, old versions, hide markers, SHA1-based duplicates, and an estimated monthly cost.

### Cleanup (destructive)
See `references/cleanup-playbook.md`. Never skip the dry-run step.

### Lifecycle rules
```bash
b2 bucket get <bucket>
b2 bucket update --lifecycle-rules '<json>' <bucket> allPrivate
```
Lifecycle rule JSON format is in `references/b2-cli-reference.md`.

### Security review
See `references/security-review.md` for the full checklist (bucket type, SSE, CORS, object lock, replication, lifecycle coverage).

## References

- `references/setup.md` — first-use setup walk-through (install, app-key creation, authorization)
- `references/cleanup-playbook.md` — safe deletion procedure with dry-run
- `references/security-review.md` — per-bucket security audit checklist
- `references/b2-cli-reference.md` — CLI v4 command reference
