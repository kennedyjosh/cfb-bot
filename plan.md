# CFB 26 Dynasty Scheduler
## Technical Planning Document
*Version 0.1 | March 2026*

---

## Table of Contents

1. [Overview](#1-overview)
2. [Problem Statement](#2-problem-statement)
3. [Key Definitions](#3-key-definitions)
4. [Season Structure](#4-season-structure)
5. [Constraints Summary](#5-constraints-summary)
6. [Technical Stack](#6-technical-stack)
7. [Feature Roadmap](#7-feature-roadmap)
   - Feature 1: Single-Season Schedule Request Optimization
   - Feature 2: Single-Season Home/Away Balancing
   - Feature 3: Multiple Concurrent Dynasties
   - Feature 4: User Self-Serve Commands
   - Feature 5: Multi-Season Home/Away Balancing and Home-and-Home Series
8. [Discord Command Structure](#8-discord-command-structure-planned)
9. [Open Questions](#9-open-questions)
10. [Out of Scope](#10-out-of-scope)

---

## 1. Overview

This document describes the design and build plan for a Discord bot that automates non-conference game scheduling for CFB 26 Dynasty mode. It captures the full problem statement, constraints, feature roadmap, and the technical decisions made during the planning process.

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

**Non-conference cap:** The maximum number of non-conference games a team can be assigned, calculated as: `12 − (number of conference games) − (number of bye weeks)`.

**Home-and-home series:** A two-season commitment in which two teams agree to play each other in back-to-back seasons, with each team serving as the home team in one season. The return game in Season 2 is treated as a hard scheduling constraint.

**Dynasty:** A single instance of a CFB 26 Dynasty save, with its own set of user-controlled teams, conferences, and season history. Multiple dynasties may run concurrently and are fully independent.

---

## 4. Season Structure

- **Weeks 1–14:** Regular season. Conference and non-conference games are played.
- **Week 15:** Reserved exclusively for Army vs. Navy. Out of scope for this tool.
- Teams typically play 8–9 conference games, though this varies by conference and is not a fixed constant.
- Teams may have bye weeks (weeks with no game scheduled).
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

In early versions (Features 1–3), all bot commands are admin-only. The admin is solely responsible for data entry, running the solver, and querying output. User-facing self-serve commands are introduced in Feature 4, at which point users may submit requests, view any team's schedule, and check home/away balance.

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
- It natively supports multi-objective optimization, allowing both "maximize fulfilled requests" and "minimize home/away imbalance" to be expressed in a single solver run with weighted objectives.
- At this problem scale (up to 32 teams, ~16 requests, 14 weeks), solve time is in the milliseconds.
- It handles hard constraints (no double-booking, cap enforcement) and soft constraints (balance objectives) cleanly within the same model.
- It is battle-tested at production scale and well-documented with Python examples.

The solver model for the core scheduling problem is structured as follows:

- **Decision variable:** a boolean for each (request, week) pair — is request R assigned to week W?
- **Hard constraint:** each request is assigned to at most one week.
- **Hard constraint:** for each team and each week, at most one game is assigned.
- **Hard constraint:** a game cannot be assigned to a week where either team has a conference game.
- **Hard constraint:** the total non-conference games assigned to a team cannot exceed their cap.
- **Objective:** maximize the sum of assigned request variables.

### 6.3 Discord Interface: discord.py

The bot is implemented as a Discord bot using slash commands via `discord.py`. In early versions, all commands are admin-only. The bot accepts conference schedule data and schedule requests through structured slash commands and outputs results as formatted Discord messages. User-facing commands are introduced in Feature 4.

### 6.4 Persistence: SQLite

A local SQLite database (single file, no server required) is used for persistence. This is necessary for multi-season features including carry-forward home/away balance tracking and home-and-home obligation management. Python's `sqlite3` module is part of the standard library — no additional dependency is required.

---

## 7. Feature Roadmap

Features are built incrementally in the following order, each shipping as a complete, usable version of the tool.

---

### Feature 1: Single-Season Schedule Request Optimization

#### Scope

The MVP. Given a single dynasty's conference schedules and a list of non-conference game requests, assign a week to as many requests as possible.

#### Inputs

- Teams and their conferences, scraped automatically from user display names in the Discord server at bot startup.
- Each team's conference schedule: a list of the weeks on which they have a conference game, entered by the admin.
- Each team's bye weeks, entered by the admin.
- A list of schedule requests in a pre-defined format, maintained by the admin in an external document and entered into the bot by the admin.

#### Outputs

- A single summary message posted to the admin listing each fulfilled request and its assigned week.
- Unfulfilled requests listed separately in the same message.
- The admin may subsequently query any individual team's schedule with a command.

#### Constraints Enforced

- No team plays twice in the same week.
- No team is assigned a non-conference game on a conference game week.
- No team exceeds their non-conference cap.
- **Objective:** maximize total fulfilled requests.

#### Notes

- CPU teams are always available and have no conference schedule.
- Home/away assignment is not considered in this version.
- Single dynasty only; no persistence required.
- Tie-breaking between equally optimal solutions is handled randomly.

---

### Feature 2: Single-Season Home/Away Balancing

#### Scope

Extend Feature 1 to also optimize the home/away assignment for each scheduled non-conference game. The goal is to minimize imbalance between home and away games for each team across the full season.

#### Inputs

- All inputs from Feature 1.
- For each team: the total number of home games in their conference schedule, entered as part of the `/conf` command.

#### Outputs

- All outputs from Feature 1.
- For each fulfilled request: which team is designated as the home team.

#### Constraints Enforced

- All hard constraints from Feature 1.
- **Soft constraint:** for each team, minimize `|home games − away games|` across all 12 games.
- Home/away balance is a secondary objective; it does not block a game from being scheduled.

#### Solver Model Extension

- Add a boolean variable per scheduled game: is Team A the home team?
- Track each team's conference home game count as a constant offset in the balance calculation.
- Add a weighted penalty term to the objective for home/away imbalance, subordinate to the primary maximize-requests objective.

---

### Feature 3: Multiple Concurrent Dynasties

#### Scope

Support multiple fully independent dynasties running simultaneously across different Discord servers. Each Discord server hosts exactly one dynasty, with its own set of teams, conferences, schedules, and request queues. No dynasty management commands are needed — the server itself is the dynasty identifier.

#### Inputs

- All inputs from Feature 2, automatically scoped to the Discord server the command is issued from.

#### Technical Notes

- Each dynasty is an isolated data context — a separate set of rows in the SQLite database keyed by Discord server (guild) ID.
- The solver is instantiated independently per dynasty; no shared state.
- Persistence (SQLite) becomes fully active in this feature, as dynasty data must survive bot restarts.
- Team names are scraped from user display names automatically at bot startup, scoped per server.

---

### Feature 4: User Self-Serve Commands

#### Scope

Open a subset of commands to all Discord server members (not just the admin). Users can submit schedule requests directly, view any team's non-conference schedule, and check home/away balance. The admin retains exclusive control over conference schedule data entry, solver execution, and season management.

#### New User-Facing Capabilities

- Submit a schedule request against any opponent directly via slash command, without going through the admin.
- View the solved non-conference schedule for any team.
- View the current home/away balance for any team.

#### Admin-Only Capabilities (Unchanged)

- Entering conference schedules and bye weeks.
- Running the solver.
- Closing the season.

#### Technical Notes

- Introduces Discord permission scoping: commands are tagged as either admin-only or available to all members.
- Request deduplication: if two users each submit a request for the same matchup, the bot should treat it as a single request.
- The admin can still enter requests manually on behalf of users (e.g., for CPU opponents or users who aren't on Discord).

---

### Feature 5: Multi-Season Home/Away Balancing and Home-and-Home Series

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

## 8. Discord Command Structure (Planned)

Commands are either admin-only or available to all users, as noted. This is a preliminary list and will be refined during implementation.

### Setup Commands *(admin-only)*

| Command | Description |
|---|---|
| `/conf <team> <weeks> <home_games>` | Enter a team's conference schedule. `weeks` is a space-separated list of week numbers (e.g. `1 3 5 7 9 11`); `home_games` is the count of home games among them. *(`home_games` argument added in Feature 2)* |

### Scheduling Commands *(admin-only)*

| Command | Description |
|---|---|
| `/request add <team1> <team2>` | Add a non-conference game request on behalf of two teams. |
| `/schedule run` | Run the solver and output the full assigned schedule to the admin. |
| `/season close` | Finalize the season, record home/away balances, and store any home-and-home obligations. *(Feature 5+)* |

### Query Commands *(all users — introduced in Feature 4)*

| Command | Description |
|---|---|
| `/request add <team1> <team2>` | Submit a schedule request (user self-serve version). |
| `/schedule show <team>` | Display the non-conference schedule for any team. |
| `/homeaway status <team>` | Show a team's home/away balance for the current season. *(Feature 2+)* |
| `/homeaway history <team>` | Show a team's cumulative home/away balance across all seasons. *(Feature 5+)* |

---

## 9. Open Questions

The following items were deferred during planning and will need to be resolved before or during implementation:

1. **Request deduplication (Feature 4):** If two users each submit a request for the same matchup independently, should the bot silently deduplicate, notify the second submitter, or flag it for the admin?
2. **Tie-breaking refinement:** Random tie-breaking is used initially. Smarter heuristics (e.g. prefer weeks earlier in the season, or prefer weeks that leave the most flexibility for remaining requests) may be worth introducing in a later pass.

---

## 10. Out of Scope

- Army/Navy Week 15 enforcement — handled outside this tool.
- Conference schedule generation — the game engine controls this.
- Bowl game and playoff scheduling.
- Any in-game automation; this tool is purely a scheduling assistant.
