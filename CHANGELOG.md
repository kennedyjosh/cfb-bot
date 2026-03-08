# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-03-08

### Added

- Home/away assignment for every scheduled non-conference game, optimized by CP-SAT to minimize per-team home/away imbalance

### Changed

- `/conference_schedule` now requires a `home_games` integer argument (number of home conference games among those weeks)
- `/schedule create` and `/schedule show` output now displays `{home} vs. {away}` or `{away} at {home}` notation; per-team view shows `vs. {opponent}` or `at {opponent}`

## [0.4.0] - 2026-03-08

### Changed

- `/schedule run` renamed to `/schedule create`

## [0.3.1] - 2026-03-08

### Changed

- Log output now includes timestamps and colors ERROR (red) and WARNING (yellow) lines for easier reading
- Set the `LOG_LEVEL` environment variable to control verbosity (e.g. `LOG_LEVEL=DEBUG` to see each member resolved or ignored during startup)
- DEBUG log lines are dimmed so they fade into the background relative to INFO/WARNING/ERROR

### Fixed

- Invalid `members.name_regex` in a guild config (e.g. PCRE-style `(?<team>...)` instead of Python `(?P<team>...)`) now logs a clear error message instead of crashing the bot on startup

## [0.3.0] - 2026-03-08

### Changed

- Team name resolution now strips punctuation and matches case-insensitively, so inputs like `"alabama"` or `"Oregon+"` resolve correctly
- Abbreviations (e.g. `App State`, `Bama`, `UNC`) are now hardcoded in the bot rather than loaded from `config/nicknames.toml`; only unambiguous school/city abbreviations are supported — mascot names are not

### Removed

- `config/nicknames.toml` — abbreviations are no longer user-editable config

## [0.2.2] - 2026-03-08

### Fixed

- Bot no longer crashes on startup due to duplicate keys in `config/nicknames.toml` (`Wildcats`, `Utes`, `Cowboys`)

## [0.2.1] - 2026-03-08

### Fixed

- Bot no longer crashes on startup when a guild has zero members

## [0.2.0] - 2026-03-08

### Added

- `make run` target: starts the bot, creating/updating the virtual environment automatically
- Startup warning logged for any guild with no per-dynasty config file

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
