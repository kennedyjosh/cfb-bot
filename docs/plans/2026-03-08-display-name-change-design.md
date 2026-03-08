# Design: Display Name Change Handling + `/request remove`

**Date:** 2026-03-08

## Overview

When a Discord member changes their display name, the bot should detect the change and update their team mapping, conference schedule, and requests accordingly. This feature also introduces `/request remove` as a primitive used both by admins and by the rename handler.

## State Layer (`bot/state.py`)

Two new methods on `GuildState`:

### `remove_request(team1, team2) -> bool`
Removes a single request matching the given pair (order-insensitive). Returns `True` if found and removed, `False` if no matching request exists. Used by `/request remove`.

### `remove_requests(team) -> list[Request]`
Removes all requests where `team_a` or `team_b` matches `team`. Returns the removed requests so the caller can re-add them with a substituted name. Used by the rename handler.

### `rename_team(old_team, new_team) -> dict`
Orchestrates a full team rename:
1. Clears `conference_schedules[old_team]` and `conference_home_games[old_team]`
2. Calls `remove_requests(old_team)` to pull out affected requests
3. Re-adds each request with `old_team` replaced by `new_team`, skipping duplicates (logged at debug)
4. Sets `last_result = None`
5. Returns `{removed: int, readded: int, skipped: int}` for upstream logging

## Bot Layer (`bot/main.py`)

### `_process_member` refactor
Extract a `_process_member(member, name_regex, ignore_regex) -> ResolvedMember | UnresolvedMember` helper. `_scrape_members` calls it in a loop with no behavior change. Being a pure-ish function (no Discord API calls), it is directly unit-testable.

### `on_member_update(before, after)`
1. If `before.display_name == after.display_name` → return immediately (silent)
2. Call `_process_member(before, ...)` and `_process_member(after, ...)` to get old and new states
3. Update `_resolved`, `_unresolved`, `_human_teams` for the guild
4. Apply state transitions based on before/after resolution:

| Before | After | Action |
|--------|-------|--------|
| resolved (old team) | resolved (new team) | `state.rename_team(old, new)` — log info |
| resolved (old team) | unresolved | `state.remove_requests(old)`, clear conf schedule, `last_result = None` — log info |
| unresolved | resolved | update mappings only — log info |
| unresolved | unresolved | update mappings only — silent |

**Note:** `last_result` is set to `None` in all cases where state changes. It becomes stale on any data change (consistent with existing behavior for conf schedule updates).

## `/request remove` Command (`bot/commands/request.py`)

New subcommand in the existing `/request` group:

- Arguments: `team1`, `team2` (both with autocomplete from `valid_teams`)
- Validates both teams exist in `valid_teams`
- Calls `state.remove_request(team1, team2)` — if `False`, responds ephemerally: "No request between {team1} and {team2} exists."
- On success: sets `last_result = None`, responds with confirmation via `fmt_request_removed` formatter

## Testing

### `bot/state.py`
- `remove_request`: happy path, not-found, order-insensitive
- `remove_requests`: removes all matching, returns removed list, leaves others intact
- `rename_team`: conf schedule cleared, requests remapped, duplicates skipped, `last_result` nulled
- Unresolved case: conf schedule and requests dropped, `last_result` nulled

### `bot/main.py`
- `_process_member` tested directly (no Discord dependency): resolved, unresolved, ignored, unparsable
- `on_member_update` permutations — each asserts the full state of `_human_teams`, `_resolved`, `_unresolved`, `conference_schedules`, `conference_home_games`, `requests`, and `last_result`:
  - old=resolved, new=resolved (same team — no-op)
  - old=resolved, new=resolved (different team — full rename)
  - old=resolved, new=unresolved
  - old=unresolved, new=resolved
  - old=unresolved, new=unresolved

### `bot/formatting.py`
- `fmt_request_removed`: new pure formatter, tested directly

### `bot/commands/request.py`
- Command handler stays thin; no new testable logic beyond state and formatting layers
- `on_member_update` is Discord framework wiring and does not require a test
