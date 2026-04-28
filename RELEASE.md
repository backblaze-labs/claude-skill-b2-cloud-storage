# Release process

One command, like `npm version`. Bumps every version field, commits, and tags.

## TL;DR

```bash
scripts/release.py patch          # 1.1.0  -> 1.1.1
scripts/release.py minor          # 1.1.0  -> 1.2.0
scripts/release.py major          # 1.1.0  -> 2.0.0
scripts/release.py 2.0.0          # explicit version

git push --follow-tags            # ship it
```

That's the whole repo-side flow. The push triggers `.github/workflows/release.yml`, which builds the `.tar.gz` + `.zip` artifacts and publishes a GitHub Release with auto-generated notes.

## What the script does

1. **Refuses to run** if the working tree is dirty or you're not on `main` (override with `--allow-dirty` / `--allow-any-branch`).
2. Reads current version from `.claude-plugin/marketplace.json` (canonical).
3. Bumps it according to `major | minor | patch | X.Y.Z`.
4. Updates the version in:
   - `b2-cloud-storage/SKILL.md` — frontmatter `metadata.version`
   - `.claude-plugin/marketplace.json` — `metadata.version` AND every `plugins[].version`
5. `git add` those two files.
6. `git commit -m "chore: release vX.Y.Z"`.
7. `git tag -a vX.Y.Z -m "Release vX.Y.Z"`.

It does **not** push. You push.

## Flags

| Flag | Effect |
|---|---|
| `--dry-run` | Print the bump; do not modify files or git. |
| `--no-tag` | Bump + commit, but skip the tag. |
| `--no-commit` | Update files only; do `git add` / commit / tag yourself. |
| `--no-changelog` | Bump + commit + tag, but skip CHANGELOG rotation. |
| `--allow-dirty` | Skip the clean-tree check. |
| `--allow-any-branch` | Skip the main/master branch check. |

## Pre-flight (one minute)

```bash
pre-commit run --all-files            # all hooks green
python -m pytest tests/ -v            # 9/9 pass
# Optionally, full Python matrix:
for v in 3.10 3.11 3.12 3.13 3.14; do
  uv run --python $v --no-project --with pytest --with pyyaml pytest tests/ -v
done
```

## CHANGELOG (automatic)

`CHANGELOG.md` follows [Keep a Changelog](https://keepachangelog.com/). The release script rotates it for you: the body of `## [Unreleased]` is moved into a new `## [X.Y.Z] - YYYY-MM-DD` section, the `[Unreleased]` heading is reset to empty, and the link references at the bottom are repointed (`[Unreleased]: ...compare/vX.Y.Z...HEAD`) with a new `[X.Y.Z]: ...compare/v<previous>...vX.Y.Z` line inserted.

**Your job:** keep `## [Unreleased]` populated as you merge PRs. The release script bundles whatever's there into the version section.

**Skip rotation:** pass `--no-changelog` (e.g. for a hotfix where the changelog entry was prepared manually).

The GitHub Release body is built by `release.yml` from auto-generated PR titles; the curated CHANGELOG.md entries are the canonical record in-repo.

## After `git push --follow-tags`

1. **GitHub Release fires automatically** from the tag (see `.github/workflows/release.yml`).
   - Artifacts: `b2-cloud-storage-vX.Y.Z.tar.gz`, `b2-cloud-storage-vX.Y.Z.zip`
   - Release notes: auto-generated from merged-PR titles since the previous tag.

2. **Directories that auto-update from GitHub** (no action needed; sync within ~24h):
   - SkillsMP
   - Claude Marketplaces
   - SkillsLLM
   - ClaudeSkills.info
   - LobeHub Skills
   - Pawgrammer Claude Skills Market
   - Agent Skills Market

3. **One directory needs a manual re-publish** — SkillHub uses CLI-uploaded snapshots, not GitHub:


   ```bash
   cd b2-cloud-storage
   npx @skill-hub/cli publish
   ```

4. **Awesome Claude Skills** — no version field in the awesome list. No re-PR needed unless the description changes meaningfully.

## Verification (24–72h)

| Where | What to check |
|---|---|
| `https://github.com/backblaze-labs/claude-skill-b2-cloud-storage/releases/tag/vX.Y.Z` | Release exists, artifacts attached, notes populated |
| `skillsmp.com` search "b2 cloud storage" | Listing reflects new description / version |
| `claudemarketplaces.com` search "backblaze" | Plugin entry version matches |
| SkillHub CLI output | `publish` printed the new live URL |
| LobeHub / Pawgrammer / Agent Skills Market listing pages | Version (from SKILL.md frontmatter) matches |

## Rolling back a bad release

```bash
git tag -d vX.Y.Z                                 # delete locally
git push origin :refs/tags/vX.Y.Z                 # delete on remote
gh release delete vX.Y.Z --yes                    # delete the GitHub Release
git revert HEAD                                   # revert the bump commit
```

If a directory has already pulled the bad version, ship `vX.Y.Z+1` immediately rather than trying to retract — most crawlers cache and a yanked version is harder to undo than overwrite.

## Why three version fields?

| Field | Who reads it |
|---|---|
| `SKILL.md` `metadata.version` | Some directory crawlers (LobeHub, Agent Skills Market) and Claude Code's skill loader. |
| `marketplace.json` `metadata.version` | claudemarketplaces.com (the marketplace as a whole). |
| `marketplace.json` `plugins[].version` | Claude Code's `/plugin marketplace add` and any tooling that consumes the per-plugin spec. |

The script keeps them in lock-step so you never have to think about which one a given consumer reads.
