---
description: Update CHANGELOG.md before a git commit. Edit the file so the changelog entry is included in the same commit as the change.
---

# Update Changelog

Update CHANGELOG.md **before** committing, so the changelog entry is part of the same commit as the change.

## Steps

1. Check the current branch: `git branch --show-current`
2. Look at what is staged: `git diff --cached --stat`
3. Read the current CHANGELOG.md
4. Decide: is this change user-facing? (see **Skip Conditions** below)
5. If yes: add one or more bullets in the correct section (see **Where to Write** below)
6. Done — do not commit here. The caller will include CHANGELOG.md in their commit.

After editing, the caller should run: `git add CHANGELOG.md` before committing.

## Where to Write

**If the current branch is `main`:** cut a release. Per project branching discipline, features are developed on branches and only land on `main` when complete — a commit to `main` is therefore a release signal. Combine the new entry with any existing `[Unreleased]` content and rename `[Unreleased]` to a versioned section (see **Choosing a Version Number** below). If there is no `[Unreleased]` section, create a versioned section directly.

**If the current branch is NOT `main`:** write to the `## [Unreleased]` section. The release will be cut when this branch merges to `main`.

When releasing a version, rename `[Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` and create a new empty `## [Unreleased]` above it.

After the release commit is made, create an annotated tag pointing to it:

```bash
git tag -a vX.Y.Z -m "Release X.Y.Z"
```

Then push the branch and tag together when network access is available:

```bash
git push --follow-tags
```

`--follow-tags` pushes the branch and any annotated tags reachable from the pushed commits in one command — no separate tag push needed.

## Choosing a Version Number

Pick the version based on what's in `[Unreleased]` relative to the last release:

| What's in [Unreleased] | Bump |
|---|---|
| Any breaking changes (renamed/removed commands, changed behavior) | MAJOR (`X+1.0.0`) |
| New features, new commands, new config keys (no breaking changes) | MINOR (`X.Y+1.0`) |
| Bug fixes only | PATCH (`X.Y.Z+1`) |

Rules:
- Any breaking change → MAJOR (even if fixes are also present)
- New features with no breaking changes → MINOR (fixes can ride along)
- Only fixes → PATCH
- **Pre-1.0 projects** (`0.x.y`): treat breaking changes as MINOR bumps (`0.Y+1.0`), not MAJOR. Stay at `0.x.y` until the project is intentionally declared stable.

A **breaking change** is anything that requires existing users to modify their workflow: renamed or removed commands, changed input format or required arguments, changed config key names, or behavior that was previously valid becoming invalid.

Look at the subsections in `[Unreleased]` to determine the bump: `### Removed` or breaking `### Changed` → at least MINOR (or MAJOR if post-1.0); `### Added` → at least MINOR; only `### Fixed` → PATCH.

## Subsections

| Subsection | Use for |
|---|---|
| `### Added` | New features, commands, config keys |
| `### Changed` | Changes to existing behavior or interfaces |
| `### Fixed` | Bug fixes |
| `### Removed` | Removed features |

If the subsection doesn't exist under the target section, create it.
If `[Unreleased]` doesn't exist at all, create it at the top of the changelog body.

## Skip Conditions — no entry needed

- Test-only changes (`test_*.py`, `conftest.py`, fixtures)
- Tooling with no behavior impact (Makefile, Dockerfile, `.gitignore`, CI config)
- Internal refactors with identical external behavior
- README or docs changes with no feature change
- Changelog edits themselves

When skipping, say so briefly: `"Tooling-only change — no changelog entry needed."`

## Style

- Keep bullets concise: one line describing the user-facing impact
- Write from the user's perspective, not the implementer's
