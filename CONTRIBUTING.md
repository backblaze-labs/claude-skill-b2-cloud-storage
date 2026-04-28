# Contributing

Thanks for working on this skill. The bar is "ship something useful for someone managing Backblaze B2 from an agent" — keep that in front when making decisions.

## Quick start (clone → green tests in ~5 min)

```bash
git clone https://github.com/backblaze-labs/claude-skill-b2-cloud-storage
cd claude-skill-b2-cloud-storage

# Conda env (team convention — see "Environment" below)
conda activate bb

# Install dev tools
pip install pre-commit pytest pyyaml ruff mypy

# One-time: register the git hook
pre-commit install

# Verify everything works
pre-commit run --all-files       # 13/13 should pass
pytest tests/ -v                 # 9/9 should pass
```

If those two commands aren't both green, **stop and fix that first**. Don't open PRs against a broken local baseline.

## Environment

The team uses a shared conda env named `bb`. If you don't have it:

```bash
conda create -n bb python=3.12          # or any 3.10–3.14
conda activate bb
pip install pre-commit pytest pyyaml ruff mypy uv
```

Why `bb` and not a project venv? Most Backblaze Labs Python work happens inside this env, and pre-commit / mypy / ruff state caches survive across projects. If you prefer a per-project venv (`python -m venv .venv && source .venv/bin/activate`), that's fine — the tooling doesn't care.

### Python version

CI runs the test matrix on **3.10, 3.11, 3.12, 3.13, 3.14**. Day-to-day development on any one of these is fine. The minimum is 3.10 — Python 3.9 reached EOL in October 2025 and isn't supported.

### Optional: `uv` for the full Python matrix locally

If you want to verify your change works on every supported version before pushing:

```bash
for v in 3.10 3.11 3.12 3.13 3.14; do
  uv run --python $v --no-project --with pytest --with pyyaml pytest tests/ -v
done
```

This is what CI does on every PR. It catches version-specific issues (e.g., a typing feature that only exists in 3.12+) before reviewers see them.

## Daily workflow

1. **Branch off `main`** with a descriptive name: `git checkout -b feat/lifecycle-rules` or `fix/sha1-grouping-edge-case`.
2. **Make changes.** Edit code, docs, configs.
3. **Add an entry to `## [Unreleased]` in `CHANGELOG.md`.** Group it under `### Added`, `### Changed`, `### Fixed`, `### Removed`, `### Deprecated`, or `### Security`. The release script bundles whatever's in `[Unreleased]` into the next version section.
4. **Run pre-commit.** Either let the git hook fire on commit, or run it ahead of time:

   ```bash
   pre-commit run --all-files
   ```

   Most hooks autofix (ruff, ruff-format, markdownlint, end-of-file-fixer, trailing-whitespace). Some don't (mypy, cspell) — fix manually if they fire.
5. **Run tests.**

   ```bash
   pytest tests/ -v
   ```

6. **Commit.** Use a [Conventional Commits](https://www.conventionalcommits.org/) prefix:
   - `feat(audit): add lifecycle-rule view command`
   - `fix(audit): handle missing contentSha1 on multipart uploads`
   - `docs: clarify per-project config in SKILL.md`
   - `chore: bump pre-commit hooks`
   - `test: add coverage for hide-marker edge case`
7. **Push and open a PR.**

## What CI runs on your PR

Three workflows fire on every push to a PR branch:

| Workflow | What it runs | Failure means |
|---|---|---|
| `ci.yml` | `pytest tests/ -v` × Python 3.10–3.14 | A test broke on at least one version. |
| `ci.yml` | `validate_frontmatter.py b2-cloud-storage/SKILL.md` | SKILL.md frontmatter is malformed or missing required fields. |
| `lint.yml` | Full pre-commit suite | A hook (ruff, markdownlint, cspell, mypy, yamllint, etc.) is unhappy. |

There's no merge-with-failing-CI escape hatch. If CI is red, the PR doesn't land.

## Style and standards

### Python

- **Type annotations are required** on every new function. The audit script uses `TypedDict` for B2 JSON shapes and the audit report — extend those rather than reaching for `dict[str, Any]` when you can.
- **No `# type: ignore`** without a reason in the comment: `# type: ignore[arg-type]  # b2 CLI returns Optional, but None means failure handled above`.
- **Ruff handles formatting** — don't fight it. If you disagree with a rule, propose a config change in a separate PR.
- **Tests for new behavior.** The b2 CLI is mocked via `patch.object(sa, "run_b2", side_effect=...)` — see `tests/test_storage_audit.py` for the pattern. Don't write tests that hit a real B2 bucket.

### Markdown

- All code fences must declare a language (` ```bash`, ` ```python`, ` ```text` for plain). Markdownlint MD040 will catch you.
- Headings, lists, and fences need surrounding blank lines. `markdownlint-cli2 --fix` autofixes these.

### Spelling

cspell flags unknown words. If a word is correct (a name, an acronym, a B2-ism, a tool name), add it to the `words` array in [`cspell.json`](cspell.json) — keep the array sorted alphabetically. Don't disable rules to suppress real misspellings.

### Security

This skill touches credentials and can delete data. Hard rules:

- **Never** commit a real B2 API key. Tests must mock `run_b2`; never hit a live endpoint.
- **Never** log or print application key values.
- **Never** add a feature that modifies `~/.b2_account_info` or any `*b2_account_info*` file.
- **Always** preserve the dry-run + explicit "yes" flow for any destructive operation.

If you find a security issue, follow [`SECURITY.md`](SECURITY.md) — don't open a public issue.

## Releasing

Releases are a one-command flow handled by [`scripts/release.py`](scripts/release.py). Full process: [`RELEASE.md`](RELEASE.md).

TL;DR for the release manager:

```bash
scripts/release.py minor          # 1.1.0 → 1.2.0; bumps versions, rotates CHANGELOG, commits, tags
git push --follow-tags            # CI builds artifacts and publishes the GitHub Release
```

Contributors don't run `release.py` — only the release manager does. As a contributor, your release-related job is keeping `## [Unreleased]` in `CHANGELOG.md` populated.

## Code review expectations

- **Human review is required.** This repo will eventually be listed on [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills), which auto-rejects AI-generated PRs. Don't let an AI write your PR description, commit messages, or code-review responses verbatim — at minimum, read and edit before posting.
- **One feature per PR.** Multi-feature PRs are hard to review and harder to revert. If your change touches three things, split it.
- **Update SKILL.md and references.** Functional changes that affect how the skill is invoked or what the user sees must update `b2-cloud-storage/SKILL.md` and any relevant `references/*.md`.
- **Update tests.** New behavior gets a test. Bug fixes get a regression test.
- **Add to CHANGELOG.md.** Every PR that changes user-visible behavior adds a line under `## [Unreleased]`. Internal-only changes (CI, lint config, dependency bumps) can be omitted from the changelog if they don't affect skill consumers.

## Useful local commands cheatsheet

```bash
# Pre-commit
pre-commit run --all-files                          # run every hook on every file
pre-commit run ruff --all-files                     # run a single hook
pre-commit autoupdate                                # bump all hook versions

# Tests
pytest tests/ -v                                     # run tests
pytest tests/test_storage_audit.py::test_audit_cost_estimation -v   # run one test
pytest tests/ -v --pdb                               # drop to debugger on failure

# Type checking
mypy b2-cloud-storage/scripts tests                  # full project mypy run

# Versioning / release tools (release manager only)
scripts/release.py --dry-run patch                   # preview a patch bump
scripts/check_version.py v1.1.0                      # verify all version fields match
scripts/build_artifacts.py v1.1.0                    # build dist/*.tar.gz + dist/*.zip locally

# Skill install (test the skill end-to-end)
cp -r b2-cloud-storage ~/.claude/skills/b2-cloud-storage
# then in Claude Code: "audit my-bucket for stale files"
```

## Where to ask questions

- **Skill behavior / B2 questions** — open a [GitHub issue](https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/issues).
- **Internal team questions** — Backblaze Slack, the AI-skills channel.
- **Bug reports** — issue with reproduction steps + b2 CLI version + Python version + OS.
- **Security disclosures** — see [`SECURITY.md`](SECURITY.md). **Don't** post these as public issues.
