# CFB 26 Dynasty Scheduler
## Technical Planning Document
*Version 0.2 | March 2026*

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Key Definitions](#3-key-definitions)
4. [Season Structure](#4-season-structure)
5. [Constraints Summary](#5-constraints-summary)
6. [Technical Stack](#6-technical-stack)
7. [Feature Roadmap](#7-feature-roadmap)
   - Feature 1+2: Single-Season Schedule Optimization with Home/Away Balancing ✅
   - Feature 3: Multiple Concurrent Dynasties (in progress)
   - Feature 4: User Self-Serve Commands
   - Feature 5: Multi-Season Home/Away Balancing and Home-and-Home Series
8. [Discord Command Structure](#8-discord-command-structure)
9. [Open Questions](#9-open-questions)
10. [Out of Scope](#10-out-of-scope)

---

## 1. Overview

This document describes the design and build plan for a Discord bot that automates non-conference game scheduling for CFB 26 Dynasty mode. It captures the full problem statement, constraints, feature roadmap, and the technical decisions made during planning and implementation.

---

## 2. Problem Statement

In CFB 26 Dynasty mode, up to 32 human users each control a Division I NCAA college football program. Each season, users frequently want to play against one another in non-conference games. However, the game engine enforces several hard constraints that make ad-hoc scheduling difficult to manage manually:

- Each team plays exactly 12 games per season.
- A team may play at most one game per week.
- Conference games are determined automatically by the game engine and cannot be changed.
- Non-conference games are freely assignable — this is where the bot operates.
- Week 15 is exclusively reserved for the Army vs. Navy game. No other teams play in Week 15. *(This constraint is managed outside the tool.)*

Given a set of schedule requests — each representing two teams that want to play each other — the bot must find a valid week for each game such that neither team already has a conference game that week, neither team is double-booked, and each team does not exceed their non-conference game cap. The primary objective is to maximize the number of fulfilled requests when not all can be accommodated simultaneously.

---

## 3. Key Definitions

**Conference game:** A game between two teams in the same conference, scheduled automatically by the game engine.

**Non-conference game:** A game between two teams from different conferences, freely scheduled by the admin using this tool.

**Schedule request:** A request submitted by one or more users for two specific teams to play each other in a given season. Requests may be human vs. human or human vs. CPU.

**Non-conference cap:** The maximum number of non-conference games a team can be assigned, calculated as: `12 − (number of conference games)`. Bye weeks are not entered explicitly — they are derived as output. Any unused NC slot simply becomes a bye week, so no admin input for bye weeks is needed.

**Home-and-home series:** A two-season commitment in which two teams agree to play each other in back-to-back seasons, with each team serving as the home team in one season. The return game in Season 2 is treated as a hard scheduling constraint.

**Dynasty:** A single instance of a CFB 26 Dynasty save, with its own set of user-controlled teams, conferences, and season history. Multiple dynasties may run concurrently and are fully independent.

---

## 4. Season Structure

- **Weeks 1–14:** Regular season. Conference and non-conference games are played.
- **Week 15:** Reserved exclusively for Army vs. Navy. Out of scope for this tool.
- Teams typically play 8–9 conference games, though this varies by conference and is not a fixed constant.
- Teams may have bye weeks (weeks with no game scheduled), which arise naturally from unfilled NC slots.
- CPU-controlled teams have no conference schedule and are considered available on any week.

---

## 5. Constraints Summary

### 5.1 Hard Constraints

These must never be violated by the scheduler:

- A team may not be scheduled for more than one game per week.
- A team may not be scheduled for a non-conference game on a week when they already have a conference game.
- A team may not exceed their non-conference cap for the season.
- Each schedule request may be assigned to at most one week.
- In a home-and-home series, the return game in Season 2 must be scheduled.

### 5.2 Soft Constraints (Optimization Objectives)

These are optimized for but do not block a valid schedule:

- Maximize the total number of fulfilled schedule requests.
- Minimize home/away imbalance for each team across the full season (conference + non-conference games combined).
- When per-season balance is unachievable, minimize cumulative home/away imbalance across all seasons.

### 5.3 Permissions

In Features 1–3, all bot commands are admin-only. The admin is solely responsible for data entry, running the solver, and querying output. User-facing self-serve commands are introduced in Feature 4, at which point users may submit requests, view any team's schedule, and check home/away balance.

---

## 6. Technical Stack

### 6.1 Language: Python

Python was selected over TypeScript/Node.js, Elixir, and Go for the following reasons:

- OR-Tools, the chosen solver library, has its best-supported and most thoroughly documented bindings in Python.
- The scheduling problem is the core of the tool; Python's ecosystem makes modeling it straightforward.
- `discord.py` is a mature, well-maintained library for building Discord bots with slash command support.
- Python's `asyncio` handles concurrent Discord interactions cleanly at the scale of this tool (up to 32 users).
- Readable, maintainable code for a logic-heavy problem domain.

Elixir was considered but ruled out: while its concurrency model and pattern matching are appealing, the Nostrum Discord library is less mature, no OR-Tools bindings exist, and the concurrency advantages are irrelevant at 32-user scale. TypeScript was ruled out due to the absence of OR-Tools bindings. Go was ruled out due to verbosity and lack of solver ecosystem.

### 6.2 Solver: Google OR-Tools (CP-SAT)

The scheduling problem is a constrained combinatorial optimization problem. OR-Tools' CP-SAT solver is the right tool because:

- It guarantees an optimal solution — no valid schedule that fulfills more requests will be missed.
- At this problem scale (up to 32 teams, ~16 requests, 14 weeks), solve time is in the milliseconds.
- It handles hard constraints (no double-booking, cap enforcement) and soft constraints (balance objectives) cleanly within the same model.
- It is battle-tested at production scale and well-documented with Python examples.

The solver runs two sequential CP-SAT passes:

**Pass 1 — week assignment:**
- **Decision variable:** a boolean for each (request, week) pair — is request R assigned to week W?
- **Hard constraint:** each request is assigned to at most one week.
- **Hard constraint:** for each team and each week, at most one game is assigned.
- **Hard constraint:** a game cannot be assigned to a week where either team has a conference game.
- **Hard constraint:** the total non-conference games assigned to a team cannot exceed their cap.
- **Objective:** maximize the sum of assigned request variables.

**Pass 2 — home/away assignment:**
- Runs on the set of scheduled games produced by Pass 1.
- **Decision variable:** a boolean per game — is team_a the home team?
- **Objective:** minimize total home/away deviation across all human teams (conference + NC games combined).

### 6.3 Discord Interface: discord.py

The bot is implemented as a Discord bot using slash commands via `discord.py`. In early versions, all commands are admin-only. The bot accepts conference schedule data and schedule requests through structured slash commands and outputs results as formatted Discord messages. User-facing commands are introduced in Feature 4.

### 6.4 Persistence: SQLite

A local SQLite database (single file, no server required) is used for persistence. This is necessary for multi-season features including carry-forward home/away balance tracking and home-and-home obligation management. Python's `sqlite3` module is part of the standard library — no additional dependency is required.

*Note: as of Feature 3 in progress, state is still in-memory only. Persistence is the remaining piece of Feature 3.*

---

## 7. Feature Roadmap

Features are built incrementally in the following order, each shipping as a complete, usable version of the tool.

---

### Features 1+2: Single-Season Schedule Optimization with Home/Away Balancing ✅

**Status: Complete.** Originally planned as two separate features; built together because the two passes are tightly coupled and there was no reason to ship without home/away balancing.

#### Scope

Given a single dynasty's conference schedules and a list of non-conference game requests, assign a week to as many requests as possible and assign home/away for each scheduled game.

#### Inputs

- Teams scraped automatically from user display names in the Discord server at bot startup; remapped automatically when display names change.
- Each team's conference schedule: the weeks with conference games and the count of home games among them, entered by the admin via `/conference_schedule`.
- A list of schedule requests maintained by the admin via `/request add` / `/request remove`.

#### Outputs

- Full results posted publicly by `/schedule create`: fulfilled count, unscheduled requests with inferred reasons, home/away imbalance warnings, per-team non-conference schedule with home/away notation.
- Per-team schedule view via `/schedule show`: conference weeks, non-conference games (once scheduled), bye weeks, and advice on how many home/away CPU games to add to fill open slots and maintain balance.

#### Constraints Enforced

- No team plays twice in the same week.
- No team is assigned a non-conference game on a conference game week.
- No team exceeds their non-conference cap.
- **Primary objective:** maximize total fulfilled requests.
- **Secondary objective:** minimize per-team home/away imbalance across conference + NC games combined.

#### Implementation Notes

- Bye weeks: derived automatically from unfilled slots; not entered explicitly by the admin. NC cap = `12 - conference_games`.
- CPU teams: auto-registered from requests; no conference schedule needed; no NC cap; still subject to the double-booking constraint.
- `/request remove` was added to allow corrections without re-entering all requests.
- `/teams` was added to show all member → team mappings and identify unrecognized display names.
- `on_member_update` was added to automatically remap team state when display names change.
- Per-dynasty configuration via TOML files (`config/<guild_id>.toml`) was introduced to support per-dynasty admin IDs, name regex, and other preferences.

---

### Feature 3: Multiple Concurrent Dynasties 🔄

**Status: In progress.** Multi-guild architecture is complete; SQLite persistence is not yet implemented.

#### Scope

Support multiple fully independent dynasties running simultaneously across different Discord servers. Each Discord server hosts exactly one dynasty, with its own set of teams, conferences, schedules, and request queues. No dynasty management commands are needed — the server itself is the dynasty identifier.

#### Done

- All commands are scoped to `guild_id`; every guild has an independent `GuildState` in memory.
- Per-dynasty configuration via `config/<guild_id>.toml`.
- Team name scraping and remapping are per-guild.

#### Remaining

- SQLite persistence: dynasty data must survive bot restarts. Currently all state is in-memory and is lost when the bot stops.
- Schema design and migration strategy for the `db/` layer.
- On-startup restore: load persisted state into memory when the bot connects to a guild.

---

### Feature 4: User Self-Serve Commands

**Status: Not started.**

#### Scope

Open a subset of commands to all Discord server members (not just the admin). Users can submit schedule requests directly, view any team's non-conference schedule, and check home/away balance. The admin retains exclusive control over conference schedule data entry, solver execution, and season management.

#### New User-Facing Capabilities

- Submit a schedule request against any opponent directly via slash command, without going through the admin.
- View the solved non-conference schedule for any team.
- View the current home/away balance for any team.

#### Admin-Only Capabilities (Unchanged)

- Entering conference schedules.
- Running the solver.
- Closing the season.

#### Technical Notes

- Introduces Discord permission scoping: commands are tagged as either admin-only or available to all members.
- Request deduplication: if two users each submit a request for the same matchup, the bot should treat it as a single request. (`has_duplicate_request` is already implemented in `GuildState`; the UX response to a duplicate from a self-serve user needs to be defined.)
- The admin can still enter requests manually on behalf of users (e.g., for CPU opponents or users who aren't on Discord).

---

### Feature 5: Multi-Season Home/Away Balancing and Home-and-Home Series

**Status: Not started.**

#### Scope

Extend the tool across multiple seasons for two related features: carry-forward home/away balance and home-and-home scheduling commitments.

#### Carry-Forward Home/Away Balance

- At season end, each team's home/away imbalance is recorded (e.g., `+2` meaning 2 extra home games).
- In subsequent seasons, this carry-forward offset is included in the balance objective. A team with a prior surplus of home games is nudged toward away assignments.
- The long-run target is cumulative balance across all seasons, not strict per-season balance.

#### Home-and-Home Series

- A home-and-home request specifies two teams and a two-season window.
- In Season 1: the game is scheduled as a normal request (soft — can be fulfilled or not).
- In Season 2: the return game becomes a hard constraint — it must be scheduled, with the home/away assignment flipped from Season 1.
- The Season 2 obligation is stored in the database at the time the Season 1 game is confirmed.
- Home-and-home assignments feed into the carry-forward balance tracking.

#### Solver Model Extension

- Add carry-forward balance offset as a constant per team in the balance penalty term.
- Add hard constraints for Season 2 home-and-home obligations before running the solver.
- Record season-end balance deltas to the database after each solver run is accepted.

---

## 8. Discord Command Structure

### Implemented Commands *(all admin-only)*

| Command | Description |
|---|---|
| `/conference_schedule <team> <weeks> <home_games>` | Enter or update a team's conference schedule. `weeks` is space-separated week numbers; `home_games` is the count of home games among them. |
| `/request add <team1> <team2>` | Add a non-conference game request. |
| `/request remove <team1> <team2>` | Remove a previously added request. |
| `/schedule create` | Run the solver and post the full schedule results publicly. |
| `/schedule show <team>` | Display one team's full schedule: conference weeks, NC games (with home/away), bye weeks, and CPU game advice. |
| `/teams` | Show all Discord members and their team assignments; lists unrecognized display names separately. |

### Planned Commands — Feature 4 *(available to all users)*

| Command | Description |
|---|---|
| `/request add <team1> <team2>` | Submit a schedule request (user self-serve). |
| `/schedule show <team>` | View any team's non-conference schedule. *(already implemented as admin-only; access widens in Feature 4)* |

### Planned Commands — Feature 5+

| Command | Description |
|---|---|
| `/season close` | Finalize the season, record home/away balances, and store any home-and-home obligations. |
| `/homeaway history <team>` | Show a team's cumulative home/away balance across all seasons. |

---

## 9. Open Questions

1. **Request deduplication UX (Feature 4):** When a user submits a request for a matchup that already exists, what should the bot say? Options: silent no-op, "already requested", or notify the admin. Needs a decision before Feature 4.

2. **Tie-breaking:** The solver uses OR-Tools' default search order when multiple optimal solutions exist. Smarter heuristics (prefer earlier weeks, prefer weeks that leave flexibility for remaining requests) may be worth exploring but are not a priority.

---

## 10. Out of Scope

- Army/Navy Week 15 enforcement — handled outside this tool.
- Conference schedule generation — the game engine controls this.
- Bowl game and playoff scheduling.
- Any in-game automation; this tool is purely a scheduling assistant.
