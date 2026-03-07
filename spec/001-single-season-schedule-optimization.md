# Feature 1 Behavior Spec
## Single-Season Schedule Request Optimization

---

## Table of Contents

1. [Startup](#1-startup)
2. [Configuration](#2-configuration)
3. [Admin Permission Model](#3-admin-permission-model)
4. [Display Name Scraping](#4-display-name-scraping)
5. [Commands](#5-commands)
   - [/conference_schedule](#51-conference_schedule)
   - [/request add](#52-request-add)
   - [/schedule](#53-schedule)
   - [/schedule show](#54-schedule-show)
   - [/teams](#55-teams)
6. [Solver](#6-solver)
7. [In-Memory State](#7-in-memory-state)

---

## 1. Startup

On startup the bot performs the following steps in order:

1. Load `config/default.toml` to establish baseline config values.
2. For each guild the bot is connected to:
   a. Load `config/<guild_id>.toml` if it exists; merge over defaults.
   b. Run display name scraping for that guild (see Section 4).
3. Begin accepting Discord interactions.

If the bot joins a new guild at runtime, steps 2a–2b are performed for that guild immediately.

---

## 2. Configuration

### 2.1 Config file locations

- `config/default.toml` — canonical list of all supported keys and their defaults. Checked into the repo. Never written at runtime.
- `config/<guild_id>.toml` — per-dynasty overrides. Created manually before first use. Not required; a guild with no config file runs entirely on defaults.

### 2.2 Supported config keys (Feature 1)

```toml
[admin]
# Discord user ID or role ID with admin privileges.
# If blank, all commands work but emit a warning on every invocation.
id = ""

[members]
# Regex applied to raw display names. Members whose display name matches
# are excluded from team scraping. Matched with re.search(), so it does
# not need to cover the full name. Always treated as case-insensitive
# regardless of flags included in the pattern.
ignore_regex = "inactive"
```

### 2.3 `config/nicknames.toml`

A static mapping of common abbreviations and alternate names to canonical team names from `teams.txt`. Loaded at startup. Not per-guild — applies globally.

Format:
```toml
[nicknames]
"App State" = "Appalachian State"
"Bama" = "Alabama"
"UNC" = "North Carolina"
"TAMU" = "Texas A&M"
"WVU" = "West Virginia"
"Noles" = "Florida State"
# ... etc.
```

Members are scraped using this mapping after the regex extracts a raw name (see Section 4). Nicknames matching is case-insensitive.

---

## 3. Admin Permission Model

### 3.1 Admin identification

The bot resolves the `admin.id` config value as follows:

- If `admin.id` matches a guild member's user ID, that user is the admin.
- If `admin.id` matches a guild role ID, any member with that role is an admin.
- If `admin.id` is blank, **all guild members are treated as admins**, but every command response includes a warning:

  > Warning: No admin is configured for this server. All commands are currently unrestricted. Set `admin.id` in `config/<guild_id>.toml` to restrict admin access.

### 3.2 Admin-only commands (Feature 1)

All commands in Feature 1 are admin-only:

- `/conference_schedule`
- `/request add`
- `/schedule`
- `/schedule show`
- `/teams`

If a non-admin user invokes any of these commands, the bot responds with an ephemeral error:

> You do not have permission to use this command.

The message is ephemeral so it is only visible to the invoker.

---

## 4. Display Name Scraping

### 4.1 When scraping runs

- At startup, for each connected guild.
- When the bot joins a new guild.
- Scraping does **not** run continuously — member changes during a session are not automatically reflected. A future feature may add a manual refresh command.

### 4.2 Scraping algorithm

For each member in the guild:

1. Apply `ignore_regex` to the member's display name using `re.search()` with `re.IGNORECASE` forced on regardless of flags in the pattern. If matched, mark the member as **ignored** and skip.
2. Apply `name_regex` (from config) to the display name. If no match or the `team` capture group is empty, mark the member as **unparsable** and skip.
3. Strip and normalize whitespace from the extracted raw name.
4. Look up the raw name in `nicknames.toml` (case-insensitive). If found, replace with the canonical name.
5. Check whether the canonical name exists in `teams.txt` (case-sensitive after normalization). If not found, mark the member as **unparsable** and skip.
6. Record the member as a **human-controlled team**: map the canonical team name to their Discord user ID.

### 4.3 Scraping output

Produces two internal collections per guild:
- `human_teams`: `dict[str, int]` — team name → Discord user ID
- `unresolved_members`: `list[Member]` — members who were ignored or unparsable, stored for `/teams`

Human-controlled teams are used by:
- `/teams` (to distinguish them from CPU teams)
- Future features (home/away tracking, self-serve commands)

Human team status has no effect on Feature 1 scheduling logic — both human and CPU teams are scheduled the same way.

---

## 5. Commands

### 5.1 `/conference_schedule`

**Access:** Admin-only
**Description:** Enter a team's conference schedule for the current season.

**Arguments:**

| Argument | Type | Description |
|---|---|---|
| `team` | String (autocomplete) | The team whose schedule is being entered. Autocomplete options are drawn from `teams.txt`. |
| `weeks` | String | Space-separated list of week numbers (1–14) on which the team has a conference game. Example: `"1 3 5 7 9 11"`. |

**Validation:**

- `team` must be a value from `teams.txt`. If not (e.g. the user bypassed autocomplete), respond with an ephemeral error: `"Unknown team: <value>. Team must be from the official team list."`
- `weeks` must parse as a whitespace-separated list of integers. If unparseable, respond with an ephemeral error: `"Could not parse weeks. Expected space-separated integers, e.g. '1 3 5 7'."`
- Each week number must be in the range 1–14. Any out-of-range value produces an ephemeral error: `"Week <n> is out of range. Valid weeks are 1–14."`
- Duplicate week numbers within a single entry are silently deduplicated.

**Behavior:**

- If a conference schedule already exists for this team in the current session, it is **replaced** (not merged). The response notes this: `"Updated conference schedule for <team>."`
- If this is a new entry: `"Conference schedule set for <team>."`
- The response includes a confirmation of what was stored: `"<team>: conference games on weeks <sorted week list>."`

**Response:** Posted publicly to the channel.

**State effect:** Stores or replaces the team's conference week set in the guild's in-memory state. Does **not** affect any existing requests or solver results.

---

### 5.2 `/request add`

**Access:** Admin-only
**Description:** Add a non-conference game request between two teams.

**Arguments:**

| Argument | Type | Description |
|---|---|---|
| `team1` | String (autocomplete) | First team. Autocomplete from `teams.txt`. |
| `team2` | String (autocomplete) | Second team. Autocomplete from `teams.txt`. |

**Validation:**

- Both teams must be values from `teams.txt`. Invalid values produce an ephemeral error per team: `"Unknown team: <value>."`
- `team1` and `team2` must be different teams. If the same team is given for both, respond with an ephemeral error: `"A team cannot be scheduled against itself."`
- A request between `team1` and `team2` is considered a **duplicate** if a request already exists in the current session with the same two teams (in either order). If a duplicate is detected, respond with an ephemeral error: `"A request between <team1> and <team2> already exists."`

**Behavior:**

- On success, appends the request to the guild's in-memory request list.
- Response: `"Request added: <team1> vs. <team2>. (Request #<n> of <total>)"`

**Response:** Posted publicly to the channel.

**State effect:** Appends one Request to the guild's in-memory state. Does **not** invalidate any prior solver result — but the next `/schedule` run will use the full current request list.

---

### 5.3 `/schedule`

**Access:** Admin-only
**Description:** Run the solver against the current conference schedules and requests. Posts the full results.

**Arguments:** None.

**Pre-run validation:**

- At least one request must exist. If the request list is empty, respond with an ephemeral error: `"No requests have been added. Use /request add to add games before running the schedule."`
- Every team appearing in a request must either have a conference schedule on record **or** be known to be a CPU team (i.e. not present in `human_teams` and not in the conference schedule). CPU teams with no conference schedule are valid and require no prior setup.
- If a human-controlled team appears in a request but has no conference schedule on record, the bot **blocks the run** and responds with an ephemeral error listing the affected teams: `"Cannot run schedule: no conference schedule found for the following teams: <list>. Use /conference_schedule to enter their schedules first."` CPU teams are exempt from this check.

**Solver execution:**

- The bot calls the solver synchronously. At Feature 1 scale, solve time is negligible.
- The solver result is stored in the guild's in-memory state, replacing any prior result.

**Response format:**

Posted publicly to the channel. Format:

```
Schedule Results — <N> of <M> requests fulfilled

Fulfilled:
  Week <w>: <team1> vs. <team2>
  Week <w>: <team1> vs. <team2>
  ...

Not scheduled:
  <team1> vs. <team2>
  ...
```

- Fulfilled games are sorted by week number, then alphabetically by team1 name within each week.
- If all requests are fulfilled, omit the "Not scheduled" section.
- If no requests are fulfilled, the "Fulfilled" section reads: `"  (none)"`

---

### 5.4 `/schedule show`

**Access:** Admin-only
**Description:** Display the non-conference schedule for a single team. Only available after `/schedule` has been run.

**Arguments:**

| Argument | Type | Description |
|---|---|---|
| `team` | String (autocomplete) | The team to look up. Autocomplete from `teams.txt`. |

**Validation:**

- `team` must be from `teams.txt`. Invalid value: ephemeral error `"Unknown team: <value>."`
- If no solver result exists yet: ephemeral error `"No schedule has been generated yet. Run /schedule first."`
- If the team has no non-conference games in the solver result (either it appeared in no requests, or all its requests were unscheduled): respond with `"<team> has no non-conference games scheduled."`

**Response format:**

Posted publicly to the channel:

```
Non-conference schedule for <team>:
  Week <w>: vs. <opponent>  (home)
  Week <w>: at <opponent>   (away)
  ...
```

Note: Home/away is not tracked in Feature 1. Use a neutral format:

```
Non-conference schedule for <team>:
  Week <w>: <team> vs. <opponent>
  Week <w>: <team> vs. <opponent>
  ...
```

Games are sorted by week number.

---

### 5.5 `/teams`

**Access:** Admin-only
**Description:** List Discord members who were excluded from team scraping — either because they matched `ignore_regex` or because their display name could not be resolved to a team in `teams.txt`. Useful for diagnosing name formatting issues.

**Arguments:** None.

**Response format:**

Posted publicly to the channel:

```
Members not mapped to a team:

Ignored (matched ignore_regex):
  <display name>
  <display name>

Unparsable (name not recognized):
  <display name>
  <display name>
```

- Display names are printed as-is, without tagging/mentioning the users.
- If all members were successfully mapped, respond: `"All members have been successfully mapped to a team."`
- If a section (Ignored / Unparsable) has no entries, omit that section.

**State effect:** None. Read-only.

---

## 6. Solver

### 6.1 Inputs

The solver receives:

- A dict of team names to `Team` objects, each containing:
  - `conference_weeks`: set of ints (weeks 1–14 with a conference game)
  - `nc_cap`: int — `12 - len(conference_weeks)`. For CPU teams, this value is not enforced (treated as unlimited).
  - `is_cpu`: bool
- A list of `Request` objects, each containing `team_a` and `team_b` (team name strings).

Any team referenced in a request but not in the teams dict is treated as a CPU team with `conference_weeks = {}` and `is_cpu = True`.

### 6.2 Decision variables

For each (request index `r`, week `w` in 1–14): a boolean variable `x[r][w]` — true if request `r` is assigned to week `w`.

### 6.3 Hard constraints

1. **One week per request:** For each request `r`, `sum(x[r][w] for w in 1..14) <= 1`.
2. **No conference game conflict:** For each request `r` and week `w`: if either team in request `r` has a conference game on week `w`, then `x[r][w] = 0` (enforced by simply excluding that week from the domain — no solver variable created for it).
3. **No double-booking:** For each team `t` (human or CPU) and week `w`: the sum of all `x[r][w]` where team `t` appears in request `r` is `<= 1`.
4. **NC cap:** For each non-CPU team `t`: `sum(x[r][w] for all r involving t, all w) <= t.nc_cap`. CPU teams have no cap — they may be scheduled as many times as the request list demands.

### 6.4 Objective

Maximize: `sum(x[r][w] for all r, w)` — i.e. maximize the number of fulfilled requests.

### 6.5 Outputs

A `SolverResult` containing:
- `assignments`: list of `(Request, week)` pairs — one per fulfilled request.
- `unscheduled`: list of `Request` objects that could not be assigned any week.

### 6.6 Tie-breaking

When multiple optimal solutions exist (same number of fulfilled requests), tie-breaking is random. No further heuristics are applied in Feature 1.

### 6.7 Edge cases

The solver must handle the following without error:

- No valid week exists for any request (all requests unscheduled — valid result).
- A team appears in multiple requests.
- A team's nc_cap is 0 (all weeks are conference games).
- All requests conflict with each other (only one can be scheduled per team per week).
- The request list contains a single request.
- A CPU team appears in multiple requests — CPU teams are subject to the same double-booking constraint as human teams: at most one game per week.

---

## 7. In-Memory State

Per guild, the bot maintains the following state in memory. This state is not persisted in Feature 1 — it resets on bot restart.

```
GuildState:
  conference_schedules: dict[str, set[int]]   # team name → conf week set
  requests: list[Request]                      # ordered list of NC game requests
  last_result: SolverResult | None             # result of most recent /schedule run
```

There is no concept of "seasons" or "current season" in Feature 1. The state represents exactly one scheduling session. Clearing state between seasons requires restarting the bot (or a future admin reset command).
