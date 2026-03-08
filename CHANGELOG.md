# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-03-08

### Added

- CP-SAT solver (`solver/`) that maximizes fulfilled non-conference game requests while enforcing conference conflict, double-booking, and NC cap constraints
- `/conference_schedule` command to enter a team's conference week set
- `/request add` command to submit a non-conference game request between two teams
- `/schedule run` command to run the optimizer and post full results publicly
- `/schedule show` command to display a single team's non-conference schedule
- `/teams` command to list Discord members who could not be mapped to a team
- Display name scraping at startup: resolves member names via configurable regex and a global nicknames table (`config/nicknames.toml`)
- Per-dynasty configuration via `config/<guild_id>.toml` with sensible defaults in `config/default.toml`
- Admin permission model: restrict commands to a user ID or role ID; warns on every invocation if unconfigured
- `make test` target: runs pytest in a `linux/amd64` Docker container (required for OR-Tools on Apple Silicon sandboxes)
- `make test-local` and `make venv` targets for fast native test runs on local machines
- `/update-changelog` project command with pre-commit hook to keep CHANGELOG.md current
