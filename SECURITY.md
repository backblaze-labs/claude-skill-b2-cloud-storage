# Security Policy

## Supported versions

Only the latest release is supported. Please upgrade before reporting an issue.

## Reporting a vulnerability

In scope: this repository's code — the `b2` command guidance in `SKILL.md`, the audit and
helper scripts under `scripts/`, the CI workflows, and the docs.

- Report it privately through GitHub. Open the repository's **Security** tab and click
  **"Report a vulnerability"** to file a private advisory.
- Please do **not** open a public issue for a security problem.

Out of scope — please report these to the party that owns them, not here:

- **The Backblaze B2 platform** (the service, the S3/B2 API, or the `b2` CLI binary) —
  report through the
  [Backblaze Trust Center](https://www.backblaze.com/company/trust-center).
- **Claude Code or the Anthropic API** — report to Anthropic through their
  [responsible disclosure program](https://www.anthropic.com/responsible-disclosure-policy).

This channel is open to anyone — Anthropic and third-party reporters alike. We investigate
reports with reasonable care: we aim to acknowledge within about 14 days and to coordinate
public disclosure within about 90 days or when a fix ships, whichever comes first. These
are best-effort targets for a community project, not a formal SLA.

## What this skill does with your data

These properties are what a reviewer or user should be able to rely on; a change to any of
them is a security-relevant change:

- It collects no data and ships no telemetry — see [Privacy](README.md#privacy).
- The skill makes no network calls of its own. It invokes the user-installed `b2` CLI,
  which talks only to Backblaze B2 with your credentials; those credentials are never read,
  logged, or transmitted by the skill — see [Security](README.md#security).
- Destructive operations are gated behind a `--dry-run` preview and an explicit "yes"
  confirmation, and operations default to read-only — see the
  [contributor security rules](CONTRIBUTING.md#security).
- The skill defines no hooks and installs no additional software.

## Hardening your own buckets

The sections above cover **vulnerability disclosure**. For hardening *your own* B2 buckets
(bucket type, encryption, CORS, object lock, lifecycle), see the operational checklist in
[`skills/b2-cloud-storage/references/security-review.md`](skills/b2-cloud-storage/references/security-review.md).
