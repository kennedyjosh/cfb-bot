# Feature 2 Design: Single-Season Home/Away Balancing

*Date: 2026-03-08*

## Overview

Extend Feature 1 to assign a home team to every scheduled non-conference game, optimizing for balance between home and away games across each team's full season (conference + non-conference combined).

## User-Facing Changes

### `/conference_schedule` command
Gains a required `home_games` integer argument: the count of home games among the team's conference weeks. Example: `/conference_schedule Alabama "1 3 5 7 9 11" 3`.

### `/schedule create` output (formerly `/schedule run`)
Games display home/away assignment using conventional notation:
- Home team listed first: `Week 3: Alabama vs. Ohio State` (Alabama is home)
- Away team listed first: `Week 3: Ohio State at Alabama` (Alabama is home)

### `/schedule show <team>` output
Shown from the queried team's perspective:
- `Week 3: vs. Ohio State` — team is home
- `Week 3: at Ohio State` — team is away

## Architecture

### Two-pass solver

Home/away assignment is fully independent of week assignment — no scheduling constraint depends on which team is home. This allows clean separation:

1. **Pass 1 (unchanged):** `solve()` assigns weeks to requests, maximizing fulfilled count.
2. **Pass 2 (new):** `assign_home_away()` takes the scheduled assignments and each team's `conference_home_games` count, then runs a second small CP-SAT model to assign home/away for each game.

Both functions live in `solver/`. The bot layer calls them in sequence.

### Home/away objective

For each human team: minimize `|total_home_games − total_away_games|` across all season games, where `total_home_games = conference_home_games + nc_home_games_assigned`.

CPU teams are "don't care" — for any game involving a CPU team, home/away is assigned purely to benefit the human team's balance. CPU teams are excluded from the balance objective.

The second solve is a small binary assignment problem (one boolean per scheduled game). At ≤32 teams and ~16 games, it is instantaneous.

## Data Model Changes

- `Team` gains `conference_home_games: int = 0` (default safe for CPU teams).
- `Assignment` gains `home_team: str` — the canonical name of the home team for that game.
- `GuildState` stores `conference_home_games` alongside the existing conference weeks per team.

## Testing

- `assign_home_away()` tested directly: perfect-balance cases, CPU-game cases, cases where perfect balance is impossible, tie-breaking.
- Updated formatting functions tested for both `vs.` and `at` output in `/schedule create` and `/schedule show`.
- `/conference_schedule` parsing tested for the new required `home_games` argument.

## Command Name Corrections

The canonical command names throughout the codebase and documentation are:
- `/conference_schedule` (not `/conf`)
- `/schedule create` (replacing `/schedule run`)

`plan.md` should be updated to reflect these names.

## Out of Scope

- `/homeaway status <team>` — introduced in Feature 4.
- Carry-forward balance across seasons — Feature 5.
- Any persistence changes — still in-memory only.
