# B2 Security Review Checklist

Run per bucket. Most data comes from `b2 bucket get <bucket>` (JSON output) plus `b2 replication status <bucket>`.

## What to check

### 1. Bucket type (`bucketType`)

- `allPrivate` — objects require authorization. Default for most use cases.
- `allPublic` — anyone with the URL can read. Only appropriate for intentionally public assets (static site files, public downloads).

**Flag** any `allPublic` bucket that contains anything that looks like user data, logs, backups, or config. Warn the user.

### 2. Server-side encryption (`defaultServerSideEncryption`)

- `mode: "SSE-B2"` with `algorithm: "AES256"` — B2-managed encryption. Recommended default.
- `mode: "SSE-C"` — customer-managed key. More control, more burden.
- `mode: "none"` — no default encryption. Flag.

Encryption is always at-rest; this check is whether a *default* is set for new uploads.

### 3. CORS rules (`corsRules`)

Each rule has `allowedOrigins`, `allowedOperations`, `allowedHeaders`, `exposeHeaders`, `maxAgeSeconds`.

**Flag** any rule that combines:
- `allowedOrigins: ["*"]` AND
- Any write operation in `allowedOperations` (`b2_upload_file`, `b2_upload_part`, `b2_delete_file_version`, or the S3-compat equivalents)

Wildcard + read-only is usually fine for public assets; wildcard + write is almost never intentional.

### 4. Object Lock / default retention (`defaultRetention`, `fileLockEnabled`)

If `fileLockEnabled: true`:
- `mode: "governance"` — users with `bypassGovernance` permission can delete.
- `mode: "compliance"` — cannot be removed until the retention period expires. Irreversible.
- `period` — how long retention applies.

For compliance-critical buckets (audit logs, regulated data), expect compliance mode. For general-purpose buckets, lock is often off.

### 5. Lifecycle rules (`lifecycleRules`)

Look at each rule's `fileNamePrefix` + `daysFromUploadingToHiding` + `daysFromHidingToDeleting`.

**Flag** buckets where the audit shows significant stale data but no lifecycle rule covers it — the user is paying to store data that has no retention policy.

### 6. Replication (`b2 replication status <bucket>`)

For buckets with replication sources/targets configured:
- Confirm the target bucket is owned by an expected account
- Confirm replication key has only the permissions it needs

### 7. Access key scope (via `b2 account get-info` — but **do not run this** per the skill's security rules)

Skip automated checks here. Instead, remind the user:
- Read-only app keys for humans / CI that only needs to consume data
- Write keys should be scoped to the specific bucket, not "All"
- Rotate keys periodically

## Output format

Report per-bucket findings in this shape:

```
Bucket: <name>
  Type: allPrivate ✓
  Default SSE: SSE-B2 AES256 ✓
  CORS rules: 2 (all read-only, no * origin) ✓
  Object Lock: disabled (no regulated data → OK)
  Lifecycle: none  ⚠  ~40 GB stale data with no rule
  Replication: none
```

Concrete flags + a recommendation beat vague "looks secure" summaries.
