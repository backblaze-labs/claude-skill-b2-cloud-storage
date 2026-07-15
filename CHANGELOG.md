# Changelog

All notable changes to this skill are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Marketplace listing-check scripts (`scripts/check_listings_api.py` HTTP probe and
  `scripts/check_listings.py` Playwright probe) and a scheduled `listings.yml` workflow
  that runs the HTTP probe weekly, publishes a status report, and fails if the repo loses
  a discovery topic.
- Workflow hardening for CI, lint, release, and listing checks: GitHub Actions are pinned
  to full commit SHAs, checkout credentials are not persisted when unused, non-release
  workflows declare read-only token permissions, and release publishing uses the GitHub CLI
  instead of a third-party action in the write-token job.
- `skills/b2-cloud-storage/.claude-plugin/plugin.json` plugin manifest, so the skill can be
  submitted to the Anthropic community plugin marketplace and pass `claude plugin validate`.
  Its `version` is kept in sync by `release.py` and enforced by `check_version.py`.
- `SECURITY.md` vulnerability-disclosure policy: in/out-of-scope reporting (private GitHub
  advisories for skill-code issues; Backblaze Trust Center for B2-platform issues; Anthropic
  for Claude Code / API issues), best-effort response targets, and a data-handling section
  (no telemetry, credentials never logged, dry-run-gated deletions, no hooks) that links to
  the README Privacy/Security and contributor security rules. Satisfies the Anthropic
  Software Directory contact/security-channel requirement.
- `.github/dependabot.yml` — weekly `github-actions` version updates that bump the
  SHA-pinned action references, complementing the existing pinning and secret-scanning /
  Dependabot-alerts settings already enabled on the repository.
- Top-level **Privacy** section in the README stating the skill collects no data and
  transmits nothing to the authors, with a link to Backblaze's privacy policy.
- **Trademarks** section in the README disclaiming Anthropic affiliation/endorsement and
  attributing the Claude, Claude Code, and Backblaze marks to their owners, aligning with
  Anthropic's trademark guidelines.

### Changed

- Trademark-compliance edits to the README: retitled the heading to "Backblaze B2 Cloud
  Storage — a skill for Claude Code" (was "Claude Skill: …", which read as a product name),
  and removed the Anthropic logo from the Claude Code badge (an unauthorized, recolored
  rendering of the mark).
- Moved the skill from `b2-cloud-storage/` to `skills/b2-cloud-storage/` so marketplace
  crawlers that scan the conventional `skills/<name>/SKILL.md` path can discover it. Release
  artifacts still root at `b2-cloud-storage/`, so install commands and URLs are unchanged.
- Fixed ZIP release artifact paths so they keep the public `b2-cloud-storage/` archive root.
- Removed agent-managed B2 CLI package installation guidance; users install the CLI themselves.

### Fixed

- License badge in the README now links to the actual `LICENSE` file (was a dead
  `LICENSE.txt` link).

## [1.2.0] - 2026-04-28

### Added

- `.claude-plugin/marketplace.json` — Claude Code plugin marketplace manifest, enabling auto-discovery on
  [claudemarketplaces.com](https://claudemarketplaces.com) and one-command install via `/plugin marketplace add`.
- `LICENSE` — explicit MIT license file (was previously declared in frontmatter only).
- `RELEASE.md` — release runbook documenting the single-command flow.
- `CHANGELOG.md` (this file).
- Release tooling under `scripts/`:
  - `release.py` — `npm version`-style bumper. Updates every version field, commits, tags.
  - `check_version.py` — verifies that a tag matches every in-tree version field; used by CI as the release gate.
  - `build_artifacts.py` — produces `.tar.gz` and `.zip` of the skill directory, excluding dev caches.
- `.github/workflows/release.yml` — fires on `v*` tag push: verifies sync, builds artifacts, publishes GitHub Release with auto-generated notes.
- `.github/workflows/lint.yml` — split out from `ci.yml`; runs the full pre-commit suite.
- Pre-commit suite (`.pre-commit-config.yaml`):
  - `pre-commit-hooks` — trailing whitespace, EOF, mixed line endings, JSON/YAML validity, large files, shebang/exec mismatch.
  - `ruff` + `ruff-format` (Python lint + format).
  - `markdownlint-cli2` with `--fix` (Markdown style).
  - `yamllint` (YAML style).
  - `cspell` (spell check) with project-specific allowlist (Backblaze, Anthropic, lobehub, skillsmp, etc.).
  - `mypy` (type checks).
- `pyproject.toml` — `[tool.ruff]`, `[tool.ruff.lint]`, `[tool.ruff.format]`, `[tool.mypy]` config.
- Full type annotations across the Python codebase:
  - `TypedDict` definitions for the B2 file-version shape and the audit report
    (`B2FileVersion`, `Thresholds`, `Counts`, `SizesBytes`, `MonthlyCost`, `PrefixInfo`, `ExtensionInfo`,
    `StaleEntry`, `LargeEntry`, `AuditReport`).
  - All 24 functions across `storage_audit.py`, `test_storage_audit.py`, and `validate_frontmatter.py` annotated.
- README badge row (CI, MIT, Python 3.10–3.14, Ruff, mypy, pre-commit, cspell, Claude Code, Agent Skills, Backblaze, GitHub stars) with an annotated `<details>` table explaining each.
- `.markdownlint-cli2.yaml`, `.yamllint.yaml`, `cspell.json` configs.
- `.mypy_cache/` and `dist/` added to `.gitignore`.

### Changed

- CI matrix expanded from Python 3.11 only to **3.10, 3.11, 3.12, 3.13, 3.14** with `fail-fast: false` and `allow-prereleases: true`.
- Documented Python support: `Python 3.9+` → `Python 3.10+` (3.9 reached EOL October 2025).
  - `b2-cloud-storage/SKILL.md` `compatibility` line.
  - `README.md` requirements section.
- `b2-cloud-storage/SKILL.md` `metadata.version`: `"1.1"` → `"1.1.0"` (full SemVer for tooling compatibility).
- `.claude-plugin/marketplace.json`: added per-plugin `version` field (`plugins[].version`); the marketplace-level `metadata.version` was already present.
- Mypy tightened: `disallow_untyped_defs`, `disallow_incomplete_defs`, `warn_return_any`, `no_implicit_optional`, `warn_unreachable` enabled.
- `b2-cloud-storage/scripts/storage_audit.py` marked executable in the git index (`100755`).

### Fixed

- README bare ` ``` ` fences now language-tagged (`text`) — resolves markdownlint MD040.
- Markdown blanks-around-headings/lists/fences across reference docs (auto-fixed by `markdownlint-cli2 --fix`).

## [1.1.0] - 2026-04-22

### Added

- Storage audit enhancements: detailed reporting (live vs. billable, by prefix, by extension), stale-file detection, large-file flagging, content-SHA1 duplicate grouping, and monthly cost estimation against `--price-per-gb-month`.
- `--json` output mode for downstream tooling.
- Configurable thresholds: `--stale-days`, `--large-mb`, `--prefix-depth`.

## [1.0.0] - 2026-03-03

### Added

- Initial public release.
- `SKILL.md` defining the skill, security rules, first-use flow, and per-project config.
- Reference docs: `setup.md`, `cleanup-playbook.md`, `security-review.md`, `b2-cli-reference.md`.
- `scripts/storage_audit.py` baseline.
- Unit tests for audit logic.
- CI workflow (lint + tests + frontmatter validation on Python 3.11).

[Unreleased]: https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/compare/v1.2.0...HEAD
[1.2.0]: https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/releases/tag/v1.0.0
