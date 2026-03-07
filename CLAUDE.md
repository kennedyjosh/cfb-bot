# CLAUDE.md — CFB 26 Dynasty Scheduler

## Project Summary

A Discord bot that optimizes non-conference game scheduling for CFB 26 Dynasty mode. Up to 32 users each control a college football team in a shared Dynasty. The bot takes each team's conference schedule and a list of requested non-conference matchups, then assigns a week to each game — maximizing the number of fulfilled requests while respecting hard scheduling constraints.

The core of the project is a constraint optimization problem solved with **Google OR-Tools (CP-SAT)**. The Discord interface is built with **discord.py**. Persistence uses **SQLite** via Python's standard library `sqlite3`.

## Key Domain Concepts

- **Season:** 15 weeks. Weeks 1–14 are playable; Week 15 (Army/Navy) is out of scope.
- **Conference game:** Assigned by the game engine. The bot reads these as busy weeks — it cannot change them.
- **Non-conference game:** Freely assignable by the bot. This is the bot's entire job.
- **Non-conference cap:** `12 - conference_games - bye_weeks` per team. The bot enforces this as a hard constraint.
- **CPU teams:** Always available. No conference schedule needed.
- **Schedule request:** A pair of teams that want to play each other. A team can appear in multiple requests.
- **Home-and-home:** A two-season commitment. Season 1 game is a soft request; Season 2 return game is a hard constraint.

## Feature Roadmap

See `plan.md` for the full feature roadmap, problem statement, and technical decisions.

## Architecture

Keep the codebase cleanly separated into three layers:

- **`solver/`** — pure Python, no Discord dependency. Takes a data model in, returns a solution out. Must be independently testable.
- **`bot/`** — Discord bot, slash commands, input parsing, output formatting. Calls into the solver layer.
- **`db/`** — SQLite data access. Schema migrations, reads, writes. No business logic here.

Do not let Discord concerns bleed into the solver, and do not put scheduling logic in the bot layer.

## Git Discipline

- Commit after every meaningful unit of work — a passing test, a completed command, a solver extension.
- Write clear, imperative commit messages: `Add /conf command with week and home_games parsing`, not `updates`.
- Use semantic versioning for releases. Maintain `CHANGELOG.md` at the project root.
- Never commit broken code to `main`. Use a feature branch per feature.

## Changelog

Maintain `CHANGELOG.md` using [Keep a Changelog](https://keepachangelog.com) format with semantic versioning:

- **MAJOR** version for breaking changes to command interfaces or data schema.
- **MINOR** version for each completed feature (Features 1–5).
- **PATCH** version for bug fixes and minor improvements within a feature.

Start at `0.1.0` when Feature 1 ships. Do not tag `1.0.0` until Feature 2 is complete and the bot is considered stable for real use.

## Testing Philosophy

Test all three layers. For the solver and db layers, test thoroughly. For the bot layer, keep command handlers thin — extract all non-trivial logic (argument parsing, input validation, response formatting) into pure functions with no Discord dependency, and test those functions directly. The only acceptable untested surface area is the Discord framework wiring itself. See `adr/004-testing-strategy.md` for the full strategy.

Run tests with `pytest` from the project root before every commit. If a test is failing and the fix is non-trivial, commit a `FIXME` note and open a follow-up — do not let a flaky test become an excuse to skip the suite.

## Per-Dynasty Configurability

Different dynasties may have different operational preferences. Before hardcoding any value that could reasonably vary between dynasties, ask: *should this be configurable per dynasty?* If yes, add it as a key in that dynasty's TOML config file.

Per-dynasty config is stored in `config/<guild_id>.toml` — one file per dynasty, created with defaults on first run. Use `tomllib` (stdlib) for reads and `tomli-w` for writes. All keys must have sensible defaults so a dynasty with no config file works out of the box. The canonical list of supported config keys and their defaults lives in `config/default.toml`. See `adr/003-per-dynasty-config.md` for the full rationale.

## Constraints & Decisions Log

Decisions made during planning that should not be revisited without good reason. Major architectural decisions are documented as ADRs in `adr/`:

- `adr/001-language-and-solver.md` — why Python and OR-Tools were chosen over alternatives.
- `adr/002-persistence-layer.md` — why SQLite was chosen over JSON, PostgreSQL, and other options.
- `adr/003-per-dynasty-config.md` — why per-dynasty configuration is stored as TOML files rather than in SQLite.
- `adr/004-testing-strategy.md` — test framework, test location, coverage approach, and what to test.

Additional constraints:

- **One dynasty per Discord server.** Guild ID is the dynasty key. No multi-dynasty-per-server complexity.
- **Admin-only for data entry and solver execution.** Users get read access and request submission in Feature 4, not before.
- **Conference schedule input is weeks + home game count only.** The specific home/away assignment per week is not tracked — only the total count matters for balance.
- **CPU teams are always available**, provided they are not already scheduled against another user that week. No conference schedule is needed or accepted for CPU teams.
