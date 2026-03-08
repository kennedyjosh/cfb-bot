# CFB 26 Dynasty Scheduler

A Discord bot that optimizes non-conference game scheduling for CFB 26 Dynasty mode. Up to 32 users each control a college football team in a shared Dynasty. The bot takes each team's conference schedule and a list of requested non-conference matchups, then assigns a week to each game — maximizing the number of fulfilled requests while respecting hard scheduling constraints.

The core scheduling problem is solved with **Google OR-Tools (CP-SAT)**. The Discord interface is built with **discord.py**.

## Requirements

- Python 3.13+
- A Discord bot token with the **Server Members Intent** enabled

## Setup

1. **Create a per-dynasty config file** (optional but recommended):
   ```
   cp config/default.toml config/<your_guild_id>.toml
   ```
   Edit the file to set `admin.id` to your Discord user ID or a role ID. The bot will log a warning at startup for any guild that has no config file. All available config keys and their defaults are documented in `config/default.toml`.

2. **Set your bot token:**
   ```
   export DISCORD_TOKEN=your_token_here
   ```

3. **Run the bot:**
   ```
   make run
   ```
   This creates a virtual environment and installs dependencies automatically on first run.

## Usage

All commands are admin-only. Set `admin.id` in `config/<guild_id>.toml` to your Discord user ID or a role ID. If unset, the bot warns on every command but allows everyone.

> **Note:** State is in-memory only — restarting the bot clears all entered schedules and requests. Persistence is a planned future feature.

### Step 1 — Enter conference schedules

```
/conference_schedule <team> <weeks> <home_games>
```

Enter each human-controlled team's conference schedule before running the solver. Repeat for every team.

- `team` — team name from the official list (autocompleted)
- `weeks` — space-separated week numbers with conference games, e.g. `1 3 5 7 9 11`
- `home_games` — how many of those weeks are home games

CPU-controlled teams don't need a conference schedule.

### Step 2 — Add game requests

```
/request add <team1> <team2>
```

Add each desired non-conference matchup. Either team can be listed first. CPU teams are valid opponents. Duplicate requests are rejected.

```
/request remove <team1> <team2>
```

Remove a previously added request.

### Step 3 — Run the scheduler

```
/schedule create
```

Runs the CP-SAT optimizer and posts the full schedule publicly. Each game is shown as `{home} vs. {away}` or `{away} at {home}`. Games that couldn't be assigned a week are listed as unscheduled.

The solver enforces:
- No game scheduled during either team's conference week
- No team double-booked in the same week
- Non-conference cap per team (`12 - conference_games`)

Home/away assignment is optimized separately to minimize per-team imbalance across conference and non-conference games combined.

### Other commands

```
/schedule show <team>
```
Show one team's non-conference schedule (e.g. `vs. Auburn` or `at Auburn`). Requires `/schedule create` to have been run first.

```
/teams
```
Show all Discord members and their team assignments (e.g. `Alabama — @Josh`). Members the bot couldn't map to a team are listed separately under "Unrecognized". The bot scrapes member display names at startup — members need a display name that matches a team name or known abbreviation. Use this to find who needs their display name fixed.

You can re-run `/conference_schedule` to update a team's schedule and re-run `/schedule create` as many times as needed.

## Development

### Running Tests

There are two ways to run tests depending on your environment.

#### Local machine (Mac/Linux with native OR-Tools support)

On a real machine, OR-Tools works natively. Set up the local venv once, then use `make test-local` for fast feedback during development:

```
make venv        # one-time setup; re-run after requirements change
make test-local  # runs pytest directly in .venv (~1s)
```

Use `make test` before committing to verify everything passes in the canonical `linux/amd64` container:

```
make test
```

#### Sandbox / AI agent environment (LinuxKit on ARM)

OR-Tools crashes with `SIGILL` in LinuxKit-based sandbox environments (e.g. Claude Code sandbox on Apple Silicon) due to CPU instruction incompatibility. Tests must run inside a `linux/amd64` Docker container. The sandbox also requires a proxy to reach PyPI.

The sandbox has a firewall — PyPI (`pypi.org:443`) must be explicitly allowed before running tests. Once allowed:

```
make test PROXY=http://host.docker.internal:3128
```

This passes the proxy through to `pip` inside the container. If the sandbox proxy re-encrypts HTTPS traffic (i.e. pip fails with a certificate error), copy the proxy CA cert to the project root and re-run — it will be picked up automatically:

```
cp /usr/local/share/ca-certificates/proxy-ca.crt ./proxy-ca.crt
make test PROXY=http://host.docker.internal:3128
```

`proxy-ca.crt` is gitignored and never committed.

### Make Targets

| Target | Description |
|---|---|
| `make run` | Run the bot (creates/updates `.venv/` automatically) |
| `make venv` | Create `.venv/` and install all dependencies including dev |
| `make test-local` | Run pytest in `.venv/` (fast; native only) |
| `make test` | Build and run tests in a `linux/amd64` Docker container |
| `make install-hooks` | Install git hooks from `hooks/` into `.git/hooks/` |

## Project Structure

```
solver/      — CP-SAT scheduling optimizer (no Discord dependency)
bot/         — Discord bot: commands, parsing, formatting, state
db/          — SQLite persistence (future feature)
config/      — Default and per-dynasty configuration
hooks/       — Git hooks (install with make install-hooks)
spec/        — Behavior specifications
adr/         — Architecture Decision Records
```
