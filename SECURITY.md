# Security Policy

## Supported versions

Only the latest release is supported. Please upgrade before reporting an issue.

## Reporting a vulnerability

**A vulnerability in this skill's code** — the `b2` command guidance in `SKILL.md`, the
audit script, CI workflows, or docs:

- Report it privately through GitHub. Open the repository's **Security** tab and click
  **"Report a vulnerability"** to file a private advisory.
- Please do **not** open a public issue for a security problem.

**A vulnerability in the Backblaze B2 platform itself** — the service, the S3/B2 API, or
the `b2` CLI binary:

- Report it through Backblaze's official channel at the
  [Backblaze Trust Center](https://www.backblaze.com/company/trust-center). It does not
  belong in this repository.

We triage reports on a best-effort basis, acknowledge them, and work with you on a fix.
This is a community project with no formal response-time SLA.

## Scope note

This file covers **vulnerability disclosure**. For hardening *your own* B2 buckets
(bucket type, encryption, CORS, object lock, lifecycle), see the operational checklist in
[`skills/b2-cloud-storage/references/security-review.md`](skills/b2-cloud-storage/references/security-review.md).
