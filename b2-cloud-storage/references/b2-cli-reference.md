# B2 CLI Quick Reference (v4.x)

B2 CLI v4 uses `b2://` URIs for bucket paths and `b2id://` for file IDs.

## Authentication

```bash
b2 account authorize                  # interactive — prompts for keyID + appKey
b2 account authorize <keyID> <appKey> # non-interactive
```

Credentials stored in `~/.b2_account_info` (SQLite). Also supports env vars:

- `B2_APPLICATION_KEY_ID`
- `B2_APPLICATION_KEY`

Per-project credential file:

```bash
B2_ACCOUNT_INFO=~/.b2_account_info_projectname b2 account authorize
B2_ACCOUNT_INFO=~/.b2_account_info_projectname b2 ls
```

## Listing

| Command | Description |
|---------|-------------|
| `b2 ls` | List all buckets |
| `b2 ls b2://<bucket>` | List top-level files/folders |
| `b2 ls -r b2://<bucket>` | List all files recursively |
| `b2 ls -r --json b2://<bucket>` | JSON output (for scripting) |
| `b2 ls b2://<bucket>/<prefix>` | List files under prefix |

## File Operations

| Command | Description |
|---------|-------------|
| `b2 file info b2id://<fileId>` | Show file metadata |
| `b2 file url b2id://<fileId>` | Get download URL |
| `b2 file download b2://<bucket>/<path> <local>` | Download a file |
| `b2 file upload <bucket> <local> <remote>` | Upload a file |
| `b2 file copy-by-id <sourceFileId> <bucket> <newName>` | Server-side copy |
| `b2 file hide b2://<bucket>/<fileName>` | Hide a file (soft delete) |
| `b2 file unhide b2://<bucket>/<fileName>` | Unhide a file |
| `b2 file cat b2://<bucket>/<path>` | Stream file to stdout |

## Deletion

| Command | Description |
|---------|-------------|
| `b2 rm -r --dry-run b2://<bucket>/<prefix>` | Preview deletions |
| `b2 rm -r b2://<bucket>/<prefix>` | Delete files (DESTRUCTIVE) |
| `b2 rm b2://<bucket>/<fileName>` | Delete single file |

## Bucket Operations

| Command | Description |
|---------|-------------|
| `b2 bucket get <bucket>` | Show bucket info (type, lifecycle, CORS, encryption) |
| `b2 bucket list` | List all buckets (alternative to `b2 ls`) |
| `b2 bucket create <name> <allPrivate\|allPublic>` | Create bucket |
| `b2 bucket update <bucket> <allPrivate\|allPublic>` | Update bucket type |
| `b2 bucket delete <bucket>` | Delete empty bucket |

## Sync

| Command | Description |
|---------|-------------|
| `b2 sync <source> <dest>` | Sync local↔B2 or B2↔B2 |
| `b2 sync --dry-run <source> <dest>` | Preview sync |
| `b2 sync --delete <source> <dest>` | Sync and delete extras at dest |

## Lifecycle Rules JSON Format

```json
[
  {
    "daysFromHidingToDeleting": 1,
    "daysFromUploadingToHiding": 90,
    "fileNamePrefix": "logs/"
  }
]
```

Apply with:

```bash
b2 bucket update --lifecycle-rules '[{"daysFromHidingToDeleting":1,"daysFromUploadingToHiding":90,"fileNamePrefix":"logs/"}]' <bucket> allPrivate
```
