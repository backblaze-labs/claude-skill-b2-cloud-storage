# B2 Setup Walk-Through

Use this when `b2 version` is missing or `b2 ls` returns an auth error.

## Step 1 — Install B2 CLI

```bash
b2 version
```

If the command is not found:
```bash
pip install b2
```

If `pip` is unavailable, try `pip3 install b2`. Verify afterwards with `b2 version`. The skill requires v4 or newer — older v3 syntax (no `b2://` URIs) is not supported.

## Step 2 — Check existing authorization

```bash
b2 ls
```

If this returns a bucket list, the CLI is already authorized — skip to project config.

If it returns an authorization error, continue.

## Step 3 — Create an application key

Tell the user:

> 1. Log in at **https://secure.backblaze.com**
> 2. Go to **App Keys** in the sidebar (or https://secure.backblaze.com/app_keys.htm)
> 3. Click **"Add a New Application Key"**
> 4. Configure the key:
>    - **Name**: anything descriptive (e.g. `claude-code-b2`)
>    - **Bucket access**: select a specific bucket OR "All"
>    - **Permissions**: for read-only use, select `listBuckets`, `listFiles`, `readFiles`. Add `writeFiles`, `deleteFiles` only if cleanup/upload is needed.
> 5. Click **"Create New Key"**
> 6. **Copy both values immediately** — the applicationKey is shown only once:
>    - `keyID` (starts with `005…` or similar)
>    - `applicationKey` (long secret string)

**Heads-up about restricted keys**: if the key is scoped to a single bucket, operations against other buckets return "bucket not found" — not "unauthorized." If the user gets surprising not-found errors, suspect the key scope.

## Step 4 — Authorize the CLI

`b2 account authorize` reads from an interactive prompt. Agents cannot drive that prompt. The user should pick one of:

**Option A — Interactive (recommended for humans).** In Claude Code, the user can run it in-session via the `!` prefix:
```
!b2 account authorize
```
This executes directly in the terminal; keys stay out of the chat transcript.

**Option B — Positional args (keys land in shell history).**
```bash
b2 account authorize <keyID> <applicationKey>
```

**Option C — Env vars (best for CI / scripts).**
```bash
export B2_APPLICATION_KEY_ID=<keyID>
export B2_APPLICATION_KEY=<applicationKey>
b2 ls
```

**Per-project credential file.** To keep keys isolated per project:
```bash
B2_ACCOUNT_INFO=~/.b2_account_info_myproject b2 account authorize <keyID> <appKey>
```
Then set `accountInfoPath: "~/.b2_account_info_myproject"` in `.claude/b2-config.json`.

## Key exposure in chat

If the user pastes their `keyID` or `applicationKey` into the chat, warn them:

> I can see your key in the chat. For security, please run `b2 account authorize` directly in your terminal (or use the `!` prefix in Claude Code). I should not see your application key. Consider rotating this key in the Backblaze console since it has been exposed.

Never echo, store, or reference key values that appear in conversation.

## Step 5 — Verify

```bash
b2 ls
```

If buckets appear, setup is done. Proceed to create the per-project config.

## Step 6 — Project config

Ask the user:
- Which bucket should be the default for this project?
- Should operations be scoped to a prefix (e.g. `data/models/`)?
- Are they using the default credential file or a per-project one?

Then write `.claude/b2-config.json` in the project root with their answers. Never include API keys in this file.

Remind the user to add `.claude/b2-config.json` to `.gitignore` — bucket names are globally unique in B2 and can be sensitive.
