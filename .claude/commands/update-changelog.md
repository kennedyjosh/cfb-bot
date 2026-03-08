---
description: Update CHANGELOG.md before a git commit. Edit the file so the changelog entry is included in the same commit as the change.
---

# Update Changelog

Update CHANGELOG.md **before** committing, so the changelog entry is part of the same commit as the change.

## Steps

1. Look at what is staged: `git diff --cached --stat`
2. Read the current CHANGELOG.md
3. Decide: is this change user-facing? (see **Skip Conditions** below)
4. If yes: add one or more bullets in the correct section (see **Where to Write** below)
5. Done — do not commit here. The caller will include CHANGELOG.md in their commit.

After editing, the caller should run: `git add CHANGELOG.md` before committing.

## Where to Write

Write to the **`## [Unreleased]`** section for in-progress work not yet assigned a version.

When a version is being released (e.g. `0.1.0`), rename `[Unreleased]` to `## [0.1.0] - YYYY-MM-DD` and create a new empty `## [Unreleased]` above it. Version releases are an intentional act — do not bump the version as part of a routine commit.

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
