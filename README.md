# CFB 26 Dynasty Scheduler

A Discord bot that optimizes non-conference game scheduling for CFB 26 Dynasty mode. Up to 32 users each control a college football team in a shared Dynasty. The bot takes each team's conference schedule and a list of requested non-conference matchups, then assigns a week to each game — maximizing the number of fulfilled requests while respecting hard scheduling constraints.

The core scheduling problem is solved with **Google OR-Tools (CP-SAT)**. The Discord interface is built with **discord.py**.

## Requirements

- Python 3.13+
- A Discord bot token with the **Server Members Intent** enabled

## Setup

1. **Install dependencies:**
   ```
   pip install -r requirements.txt
   ```

2. **Create a per-dynasty config file** (optional but recommended):
   ```
   cp config/default.toml config/<your_guild_id>.toml
   ```
   Edit the file to set `admin.id` to your Discord user ID or a role ID.

3. **Set your bot token:**
   ```
   export DISCORD_TOKEN=your_token_here
   ```

4. **Run the bot:**
   ```
   python main.py
   ```

## Configuration

Config is stored in `config/<guild_id>.toml` (one file per Dynasty server). All keys have sensible defaults defined in `config/default.toml`.

| Key | Default | Description |
|---|---|---|
| `admin.id` | `""` | Discord user ID or role ID with admin privileges. If blank, all commands work but emit a warning. |
| `members.ignore_regex` | `"inactive"` | Members whose display name matches this regex (case-insensitive) are excluded from team scraping. |
| `members.name_regex` | `"^(?P<team>.+)$"` | Regex to extract a team name from a Discord display name. Must contain a `team` named capture group. |

Team name abbreviations (e.g. "App State" → "Appalachian State") are configured globally in `config/nicknames.toml`.

## Commands

All commands are admin-only in the current release.

| Command | Description |
|---|---|
| `/conference_schedule <team> <weeks>` | Enter a team's conference schedule. `weeks` is a space-separated list of week numbers (1–14). |
| `/request add <team1> <team2>` | Add a non-conference game request between two teams. |
| `/schedule run` | Run the optimizer and post the full schedule results. |
| `/schedule show <team>` | Show the non-conference schedule for a single team. |
| `/teams` | List Discord members who could not be mapped to a team. |

## How It Works

1. The admin enters each human-controlled team's conference schedule with `/conference_schedule`.
2. The admin adds desired non-conference matchups with `/request add`.
3. `/schedule run` feeds all inputs to the CP-SAT solver, which maximizes the number of fulfilled requests while enforcing:
   - No game scheduled during either team's conference week
   - No team double-booked in the same week
   - Non-conference cap enforced (`12 - conference_games` per team)
4. Results are posted publicly to the channel.

## Running Tests

Tests run inside a `linux/amd64` Docker container (required for OR-Tools compatibility):

```
make test
```

## Project Structure

```
solver/      — CP-SAT scheduling optimizer (no Discord dependency)
bot/         — Discord bot: commands, parsing, formatting, state
db/          — SQLite persistence (future feature)
config/      — Default and per-dynasty configuration
spec/        — Behavior specifications
adr/         — Architecture Decision Records
```
