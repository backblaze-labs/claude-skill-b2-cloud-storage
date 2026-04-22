# B2 Cleanup Playbook

Destructive operations. Never skip the dry-run step.

## Procedure

1. **Identify what to delete.** Typically this follows an audit (`python scripts/storage_audit.py <bucket>`) that surfaced stale files, old versions, unfinished uploads, or duplicates.

2. **Run a dry-run first.** This lists what *would* be deleted without deleting anything:
   ```bash
   b2 rm -r --dry-run b2://<bucket>/<prefix>
   ```

3. **Show the output to the user.** Summarize: count, total size, any surprises.

4. **Ask for explicit "yes" confirmation.** Not "sure?" or "sounds good" — the user must type "yes". If they say anything else, abort.

5. **Execute the real deletion.**
   ```bash
   b2 rm -r b2://<bucket>/<prefix>
   ```

6. **Verify.** Re-run `b2 ls` or the audit to confirm the expected state.

## Cleaning up specific categories

### Unfinished large files (common source of surprise bills)

```bash
b2 file large unfinished list <bucket>                  # preview
b2 file large unfinished cancel <bucket>                # cancels all unfinished for that bucket
```

Individual unfinished files can be cancelled by fileId:
```bash
b2 file large unfinished cancel --file-id <fileId>
```

### Old versions

By default, B2 keeps every version. To remove old versions of a specific file:
```bash
b2 ls --versions b2://<bucket>/<path>                   # see all versions
b2 rm b2id://<oldFileId>                                # delete a specific version
```

For bucket-wide version cleanup, a lifecycle rule is usually the right tool (see below).

### Hidden files

`b2 file hide` creates a hide marker — the underlying bytes still exist and are billed until the hide marker is also deleted or a lifecycle rule removes them.

```bash
b2 ls --versions b2://<bucket> | grep hide              # find hide markers
```

### Using lifecycle rules instead of ad-hoc deletes

For repeatable cleanup (e.g. "delete anything in logs/ older than 90 days"), a lifecycle rule is more durable than running `b2 rm` on a schedule:

```bash
b2 bucket update --lifecycle-rules \
  '[{"daysFromHidingToDeleting":1,"daysFromUploadingToHiding":90,"fileNamePrefix":"logs/"}]' \
  <bucket> allPrivate
```

Verify with `b2 bucket get <bucket>`.

## Bucket deletion

```bash
b2 bucket delete <bucket>
```

Fails if the bucket is not empty. To empty it first:
```bash
b2 rm -r --dry-run b2://<bucket>/                       # preview ALL contents
b2 rm -r b2://<bucket>/                                 # empty it
b2 bucket delete <bucket>
```

Confirm twice for bucket deletion — it's irreversible and frees the bucket name for anyone else globally.
