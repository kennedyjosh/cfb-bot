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
- **`main.py`** — entry point. Reads `DISCORD_TOKEN` from the environment and starts the bot.

Do not let Discord concerns bleed into the solver, and do not put scheduling logic in the bot layer.

## Git Discipline

### Branching — THIS IS MANDATORY, NOT OPTIONAL

**Every feature MUST be developed on a dedicated branch. Never commit feature work directly to `main`.**

The workflow is:
1. Create a branch: `git checkout -b feature/<short-name>`
2. Commit freely on the branch — small, frequent commits are encouraged
3. When the feature is complete and all tests pass, squash the branch into a single commit and merge that into `main`: `git merge --squash feature/<short-name> && git commit`
4. Delete the feature branch after merging

**No merge commits.** `main` must have a clean, linear history. Never use `git merge --no-ff` or leave merge commits in the log.

`main` must always be in a working, releasable state. If you are ever committing directly to `main`, stop and ask whether you should be on a branch.

### Commits

- Commit after every meaningful unit of work — a passing test, a completed command, a solver extension.
- Write clear, imperative commit messages: `Add /conference_schedule command with week and home_games parsing`, not `updates`.
- Never commit broken code to `main` (or to any branch that will be immediately merged).
- Before every commit, the `/update-changelog` hook will fire if CHANGELOG.md is not staged. Update it first, then include it in the same commit.

## Running Tests

OR-Tools crashes with `SIGILL` when run natively in this sandbox (aarch64/LinuxKit CPU instruction incompatibility). **Do not run pytest directly.** Always use Docker:

```bash
# Required once per sandbox session — copy the proxy CA cert to the project root
cp /usr/local/share/ca-certificates/proxy-ca.crt /Users/josh/Code/cfb-bot/proxy-ca.crt

# Run the full test suite
make test PROXY=http://host.docker.internal:3128
```

`pypi.org:443` must be allowed through the sandbox firewall before the first run. Subsequent runs use the Docker layer cache and are fast. All tests should pass. If they don't, investigate before proceeding — do not skip or work around failures.

## Testing Philosophy — THIS IS NON-NEGOTIABLE

**Test all three layers. For the solver and db layers, test thoroughly. For the bot layer, keep command handlers thin — extract all non-trivial logic (argument parsing, input validation, response formatting) into pure functions with no Discord dependency, and test those functions directly. The only acceptable untested surface area is the Discord framework wiring itself. See `adr/004-testing-strategy.md` for the full strategy.**

Always run the full test suite (via `make test`) before merging any branch. If a test is failing and the fix is non-trivial, commit a `FIXME` note and open a follow-up — but do not let a failing test become an excuse to skip the suite, and do not merge with failing tests.

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
- **Admin-only for data entry and solver execution.** Non-admin access is not yet implemented.
- **Conference schedule input is weeks + home game count only.** The specific home/away assignment per week is not tracked — only the total count matters for balance.
- **CPU teams are always available**, provided they are not already scheduled against another user that week. No conference schedule is needed or accepted for CPU teams.
