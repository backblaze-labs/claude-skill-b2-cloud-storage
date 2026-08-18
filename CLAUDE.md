# CLAUDE.md

Guidance for AI agents (and humans) working in this repo. For the full
contributor workflow (local setup, the test matrix, releases) see
[CONTRIBUTING.md](CONTRIBUTING.md); this file captures conventions that are easy
to break by accident.

## Layout

- `skills/b2-cloud-storage/` is the shipped Claude Code skill (its `scripts/` are
  the skill runtime).
- Repo-root `scripts/` and `tests/` are the marketplace-listing tooling and the
  repo's own quality and security checks; they are not part of the shipped skill.

## CI conventions

Dependabot PRs must never run CI. Every workflow with a `pull_request:` trigger
(`ci.yml`, `lint.yml`) guards each job with this condition:

```yaml
if: ${{ github.actor != 'dependabot[bot]' && github.event.pull_request.user.login != 'dependabot[bot]' }}
```

The `github.actor` clause blocks the initial Dependabot run; the
`github.event.pull_request.user.login` clause keeps jobs skipped even if a human
later re-runs the workflow or pushes to the Dependabot branch. GitHub cannot
filter `on:` by actor (and `pull_request` branch filters match the base branch,
not Dependabot's head branch), so this job-level guard is the mechanism. Preserve
it on any workflow edit, and add it to every new `pull_request`-triggered
workflow. `listings.yml` and `release.yml` have no `pull_request` trigger, so
Dependabot never invokes them and they need no guard.

A guarded job still shows as "skipped" on the PR (no compute runs). If a check is
marked required under branch protection, a skipped check can block merge of a
Dependabot PR. CodeQL "default setup" is a repo Security setting rather than a
workflow file, so this guard does not cover it.

Run the full check suite locally before pushing (this mirrors `ci.yml` +
`lint.yml`):

```bash
pre-commit run --all-files
pytest tests/
python tests/validate_frontmatter.py skills/b2-cloud-storage/SKILL.md
```

## Workflow-security invariants

`tests/test_workflow_security.py` enforces repo security policy; keep it green
when touching `.github/workflows/`:

- Every `uses:` is pinned to a full 40-character commit SHA. Local `./`
  references are exempt.
- Non-release workflows declare read-only `contents` permission (`read`, or the
  `read-all` top-level shorthand). Workflows that legitimately need write access
  are listed in `WRITE_PERMISSION_WORKFLOW_EXEMPTIONS`.
- `actions/checkout` steps set `persist-credentials: false`.
- Steps in write-token jobs use only trusted namespaces (`actions/`, `github/`)
  and are SHA-pinned.

## Commits

One-line messages with a conventional prefix (`fix:`, `feat:`, `docs:`, `ci:`,
`test:`, `chore:`). No AI-attribution trailers.
