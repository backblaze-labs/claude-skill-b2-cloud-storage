---
name: b2-cloud-storage
description: Manage Backblaze B2 cloud storage — list files, audit usage, clean up stale data, review security posture, and manage lifecycle rules. Use when the user mentions B2, Backblaze, object storage buckets, or storage cleanup.
license: MIT
compatibility: Requires b2 CLI v4+ (pip install b2) and Python 3.9+.
metadata:
  author: jdeleon
  version: "1.0"
allowed-tools: Bash(b2:*) Bash(python:*) Read Grep Glob
disable-model-invocation: true
---

# B2 Cloud Storage Management

Manage Backblaze B2 cloud storage: list files, audit usage, clean up stale data, and review security posture.

## Security Rules (MANDATORY)

1. **Never** run `b2 account get` or `b2 key *` — these expose credentials
2. **Never** display `accountAuthToken`, `applicationKey`, or `accountId` values — if any command output contains these, redact them before showing the user
3. **Always** run `b2 rm --dry-run` first before any real deletion; require the user to explicitly confirm with "yes" before executing the actual delete
4. **Never** change a bucket to `allPublic` without warning the user about the security implications and getting explicit confirmation
5. **Default to read-only operations** — only perform writes/deletes when the user explicitly requests them
6. **Never** store or write API keys, application keys, or account IDs to any file

## Project-Level Configuration

The skill supports per-project B2 configuration. On first use in a project, ask the user which bucket and credentials to use, then save to `.claude/b2-config.json` in the project root:

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

### How it works
1. On activation, check if `.claude/b2-config.json` exists in the current project
2. If it exists, read it and use the `bucket` and `prefix` as defaults (user can still override per-command)
3. If `accountInfoPath` is set and differs from the default, export `B2_ACCOUNT_INFO` before running b2 commands:
   ```bash
   B2_ACCOUNT_INFO=<accountInfoPath> b2 ls
   ```
4. If no config exists, ask the user:
   - Which bucket do you want to work with?
   - Do you want to scope to a prefix?
   - Are you using the default B2 credentials or a separate key for this project?
5. Save their answers to `.claude/b2-config.json`

**IMPORTANT**: The config file stores bucket names and file paths only — never API keys or secrets.

## Setup & Onboarding

On first use, or if any command fails with an auth error, walk the user through setup:

### Step 1: Check if B2 CLI is installed, install if missing
```bash
b2 version
```
If the command is not found, install it:
```bash
pip install b2
```
If `pip` is not available, try `pip3 install b2`. After install, verify with `b2 version`.

### Step 2: Check if already authorized
```bash
b2 ls
```
If this returns a bucket list, the user is already set up — skip to project config. If it returns an authorization error, continue to Step 3.

### Step 3: Guide the user to create API keys
Tell the user:

> You need a Backblaze B2 application key. Here's how to get one:
>
> 1. Log in at **https://secure.backblaze.com/b2_buckets.htm**
> 2. Go to **App Keys** in the left sidebar (or visit https://secure.backblaze.com/app_keys.htm)
> 3. Click **"Add a New Application Key"**
> 4. Configure the key:
>    - **Name**: anything descriptive (e.g. `claude-code-b2`)
>    - **Bucket access**: select a specific bucket or "All" depending on your needs
>    - **Permissions**: for read-only use, select only `listBuckets`, `listFiles`, `readFiles`. Add `writeFiles`, `deleteFiles` only if you need cleanup/upload capabilities.
> 5. Click **"Create New Key"**
> 6. **Copy both values immediately** — the application key is shown only once:
>    - `keyID` (starts with `005...` or similar)
>    - `applicationKey` (the long secret string)

### Step 4: Authorize the CLI
Ask the user to paste their keyID and applicationKey when prompted:
```bash
b2 account authorize
```
This prompts interactively for the keyID and applicationKey. Credentials are stored locally in `~/.b2_account_info`.

For a project-specific credential file:
```bash
B2_ACCOUNT_INFO=~/.b2_account_info_projectname b2 account authorize
```

**IMPORTANT**: If the user pastes their key values into the chat instead of the terminal prompt, immediately warn them:
> "I can see your key in the chat. For security, please run `b2 account authorize` directly in your terminal instead. I should not see your application key. Consider rotating this key in the Backblaze console since it was exposed."

Never echo, store, or reference key values that appear in conversation.

### Step 5: Verify
```bash
b2 ls
```
If buckets appear, setup is complete. Proceed to set up project config.

## Available Actions

### List & Search Objects
```bash
b2 ls b2://<bucket>                   # list top-level
b2 ls -r b2://<bucket>               # list all files recursively
b2 ls -r --json b2://<bucket>        # JSON output for processing
b2 ls b2://<bucket>/<prefix>         # filter by prefix
```

### Inspect File Metadata
```bash
b2 file info b2id://<fileId>          # full metadata for a file
```

### Storage Audit
Run the audit script to get a structured report on storage usage, stale files, large files, and potential duplicates:
```bash
python scripts/storage_audit.py <bucket>
```

### Cleanup (Destructive — requires confirmation)
1. First, always dry-run: `b2 rm -r --dry-run b2://<bucket>/<prefix>`
2. Show the user what would be deleted
3. Ask for explicit "yes" confirmation
4. Only then execute: `b2 rm -r b2://<bucket>/<prefix>`

### Lifecycle Rules
```bash
b2 bucket get <bucket>                            # view current rules
b2 bucket update --lifecycle-rules '<json>' <bucket> allPrivate  # update rules
```
Refer to `references/b2-cli-reference.md` for lifecycle rule JSON format.

### Security Review
Check these for each bucket:
- **Bucket type**: `allPrivate` vs `allPublic` (`b2 bucket get`)
- **Encryption**: server-side encryption settings
- **CORS rules**: check for overly permissive origins
- **File lock**: retention/legal hold settings
- **Lifecycle rules**: ensure data has appropriate expiration

## References

Read this file for detailed B2 CLI v4 command syntax:
- `references/b2-cli-reference.md`
