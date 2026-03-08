---
description: Update CHANGELOG.md after a git commit. Adds bullets under [Unreleased] for user-facing changes. Skip tooling/test-only commits.
---

# Update Changelog

After making a git commit, record any user-facing change in CHANGELOG.md.

## Steps

1. Read the most recent commit: `git log -1 --format="%s%n%n%b"`
2. Read the current CHANGELOG.md
3. Decide: is this commit user-facing? (see **Skip Conditions** below)
4. If yes: add one or more bullets under `## [Unreleased]` in the correct subsection
5. Commit: `git add CHANGELOG.md && git commit -m "Update changelog: <brief description>"`

## Subsections

| Subsection | Use for |
|---|---|
| `### Added` | New features, commands, config keys |
| `### Changed` | Changes to existing behavior or interfaces |
| `### Fixed` | Bug fixes |
| `### Removed` | Removed features |

If the subsection doesn't exist under `[Unreleased]`, create it.
If `[Unreleased]` doesn't exist at all, create it at the top of the changelog body.

## Skip Conditions — no entry needed

- Test-only changes (`test_*.py`, `conftest.py`, fixtures)
- Tooling with no behavior impact (Makefile, Dockerfile, `.gitignore`, CI config)
- Internal refactors with identical external behavior
- README or docs changes with no feature change
- Changelog commits themselves

When skipping, say so briefly: `"Tooling-only commit — no changelog entry needed."`

## Rules

- **Always write to `[Unreleased]`** — never to a versioned section
- **Never bump the version** — version releases are a separate, intentional action
- Keep bullets concise: one line describing the user-facing impact
- Base the bullet on the commit message, not the implementation details
