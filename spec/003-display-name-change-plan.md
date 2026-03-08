# Feature 3: Display Name Change Handling + `/request remove` Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** When a Discord member changes their display name, update their team mapping, conference schedule, and requests automatically; also add `/request remove` as an admin command and the internal primitive that powers the rename handler.

**Architecture:** Three-layer change. State layer gains `remove_request`, `remove_requests`, and `rename_team` methods. Bot layer gains a `_process_member` pure helper (extracted from `_scrape_members`) and an `on_member_update` event handler. Command layer gains `/request remove` backed by `fmt_request_removed` in formatting.

**Tech Stack:** Python 3.13, discord.py, pytest

---

## Before You Start

Read these files to understand existing code:
- `bot/state.py` — GuildState (conference_schedules, conference_home_games, requests, last_result)
- `bot/tests/test_state.py` — existing state tests
- `bot/main.py` — CFBBot, `_scrape_members`, `ResolvedMember`, `UnresolvedMember`
- `bot/parsing.py` — `parse_display_name`
- `bot/formatting.py` — existing formatters
- `bot/tests/test_formatting.py` — formatting tests
- `bot/commands/request.py` — existing `/request add` command
- `solver/model.py` — `Request` dataclass

Run tests before starting to confirm baseline passes:
```bash
make test-local
```
All 108 tests should pass.

---

## Task 1: Create feature branch

**Step 1: Create and switch to feature branch**
```bash
git checkout -b feature/display-name-change
```

**Step 2: Verify you're on the right branch**
```bash
git branch --show-current
# Expected: feature/display-name-change
```

---

## Task 2: Add `remove_request` to `GuildState`

**Files:**
- Modify: `bot/state.py`
- Modify: `bot/tests/test_state.py`

Removes a single request matching the given pair (order-insensitive). Returns `True` if found and removed, `False` if not found.

**Step 1: Write the failing tests**

Add a new class to `bot/tests/test_state.py`:

```python
class TestRemoveRequest:
    def test_removes_matching_request(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        result = state.remove_request("Alabama", "Auburn")
        assert result is True
        assert len(state.requests) == 0

    def test_returns_false_when_not_found(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        result = state.remove_request("Alabama", "Georgia")
        assert result is False
        assert len(state.requests) == 1

    def test_order_insensitive(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        result = state.remove_request("Auburn", "Alabama")
        assert result is True
        assert len(state.requests) == 0

    def test_only_removes_matching_request(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        state.add_request("Georgia", "LSU")
        state.remove_request("Alabama", "Auburn")
        assert len(state.requests) == 1
        assert state.requests[0].team_a == "Georgia"

    def test_returns_false_when_empty(self):
        state = GuildState()
        assert state.remove_request("Alabama", "Auburn") is False
```

**Step 2: Run tests to verify they fail**
```bash
make test-local
# Expected: 5 failures on TestRemoveRequest (AttributeError: 'GuildState' has no attribute 'remove_request')
```

**Step 3: Implement `remove_request` in `bot/state.py`**

Add after `has_duplicate_request`:

```python
def remove_request(self, team1: str, team2: str) -> bool:
    """Remove the request matching the given pair (order-insensitive).

    Returns True if found and removed, False if not found.
    """
    pair = frozenset({team1, team2})
    for i, r in enumerate(self.requests):
        if frozenset({r.team_a, r.team_b}) == pair:
            self.requests.pop(i)
            return True
    return False
```

**Step 4: Run tests to verify they pass**
```bash
make test-local
# Expected: all 113 tests pass
```

**Step 5: Commit**
```bash
git add bot/state.py bot/tests/test_state.py
git commit -m "Add GuildState.remove_request"
```

---

## Task 3: Add `remove_requests` to `GuildState`

**Files:**
- Modify: `bot/state.py`
- Modify: `bot/tests/test_state.py`

Removes all requests involving a team and returns them so the caller can re-add with a substituted name.

**Step 1: Write the failing tests**

Add a new class to `bot/tests/test_state.py`:

```python
class TestRemoveRequests:
    def test_removes_all_requests_for_team(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        state.add_request("Alabama", "Georgia")
        removed = state.remove_requests("Alabama")
        assert len(removed) == 2
        assert len(state.requests) == 0

    def test_returns_removed_requests(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        removed = state.remove_requests("Alabama")
        assert removed[0].team_a == "Alabama"
        assert removed[0].team_b == "Auburn"

    def test_leaves_unrelated_requests_intact(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        state.add_request("Georgia", "LSU")
        state.remove_requests("Alabama")
        assert len(state.requests) == 1
        assert state.requests[0].team_a == "Georgia"

    def test_removes_when_team_is_team_b(self):
        state = GuildState()
        state.add_request("Auburn", "Alabama")
        removed = state.remove_requests("Alabama")
        assert len(removed) == 1
        assert len(state.requests) == 0

    def test_returns_empty_list_when_no_match(self):
        state = GuildState()
        state.add_request("Georgia", "LSU")
        removed = state.remove_requests("Alabama")
        assert removed == []

    def test_returns_empty_list_when_no_requests(self):
        state = GuildState()
        assert state.remove_requests("Alabama") == []
```

**Step 2: Run tests to verify they fail**
```bash
make test-local
# Expected: 6 failures on TestRemoveRequests
```

**Step 3: Implement `remove_requests` in `bot/state.py`**

Add after `remove_request`:

```python
def remove_requests(self, team: str) -> list[Request]:
    """Remove all requests involving ``team``. Returns the removed requests."""
    kept: list[Request] = []
    removed: list[Request] = []
    for r in self.requests:
        if r.team_a == team or r.team_b == team:
            removed.append(r)
        else:
            kept.append(r)
    self.requests = kept
    return removed
```

**Step 4: Run tests to verify they pass**
```bash
make test-local
# Expected: all 119 tests pass
```

**Step 5: Commit**
```bash
git add bot/state.py bot/tests/test_state.py
git commit -m "Add GuildState.remove_requests"
```

---

## Task 4: Add `rename_team` to `GuildState`

**Files:**
- Modify: `bot/state.py`
- Modify: `bot/tests/test_state.py`

Orchestrates the full rename: clears conf schedule, remaps requests, nulls `last_result`. Returns a summary dict.

**Step 1: Write the failing tests**

Add a new class to `bot/tests/test_state.py`. Import `SolverResult` and `Assignment` at the top if not already imported:

```python
from solver.model import Assignment, Request, SolverResult
```

Then add:

```python
def _mock_result() -> SolverResult:
    """Helper: a non-None SolverResult for testing last_result nulling."""
    return SolverResult(assignments=[], unscheduled=[])


class TestRenameTeam:
    def test_clears_conf_schedule_for_old_team(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=2)
        state.rename_team("Alabama", "Auburn")
        assert "Alabama" not in state.conference_schedules
        assert "Alabama" not in state.conference_home_games

    def test_does_not_clear_other_teams_conf_schedule(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=2)
        state.set_conference_schedule("Georgia", [2, 4], home_games=1)
        state.rename_team("Alabama", "Auburn")
        assert "Georgia" in state.conference_schedules

    def test_remaps_requests_to_new_team(self):
        state = GuildState()
        state.add_request("Alabama", "Notre Dame")
        state.rename_team("Alabama", "Auburn")
        assert len(state.requests) == 1
        pair = {state.requests[0].team_a, state.requests[0].team_b}
        assert pair == {"Auburn", "Notre Dame"}

    def test_remaps_requests_where_team_is_team_b(self):
        state = GuildState()
        state.add_request("Notre Dame", "Alabama")
        state.rename_team("Alabama", "Auburn")
        pair = {state.requests[0].team_a, state.requests[0].team_b}
        assert pair == {"Auburn", "Notre Dame"}

    def test_skips_duplicate_on_readd(self):
        state = GuildState()
        state.add_request("Alabama", "Notre Dame")
        state.add_request("Auburn", "Notre Dame")  # will collide after rename
        summary = state.rename_team("Alabama", "Auburn")
        assert summary["skipped"] == 1
        # Auburn vs Notre Dame should appear exactly once
        pairs = [frozenset({r.team_a, r.team_b}) for r in state.requests]
        assert pairs.count(frozenset({"Auburn", "Notre Dame"})) == 1

    def test_nulls_last_result(self):
        state = GuildState()
        state.last_result = _mock_result()
        state.rename_team("Alabama", "Auburn")
        assert state.last_result is None

    def test_returns_summary_dict(self):
        state = GuildState()
        state.add_request("Alabama", "Notre Dame")
        state.add_request("Alabama", "Georgia")
        summary = state.rename_team("Alabama", "Auburn")
        assert summary["removed"] == 2
        assert summary["readded"] == 2
        assert summary["skipped"] == 0

    def test_no_op_when_old_team_has_no_data(self):
        state = GuildState()
        state.add_request("Georgia", "LSU")
        state.set_conference_schedule("Georgia", [1, 2], home_games=1)
        state.last_result = _mock_result()
        summary = state.rename_team("Alabama", "Auburn")
        # Georgia's data untouched; last_result still nulled
        assert "Georgia" in state.conference_schedules
        assert len(state.requests) == 1
        assert summary == {"removed": 0, "readded": 0, "skipped": 0}
        assert state.last_result is None
```

**Step 2: Run tests to verify they fail**
```bash
make test-local
# Expected: failures on TestRenameTeam
```

**Step 3: Implement `rename_team` in `bot/state.py`**

Add after `remove_requests`:

```python
def rename_team(self, old_team: str, new_team: str) -> dict:
    """Rename a team: clear their conf schedule, remap their requests, null last_result.

    Returns {"removed": int, "readded": int, "skipped": int}.
    """
    # Clear conference schedule
    self.conference_schedules.pop(old_team, None)
    self.conference_home_games.pop(old_team, None)

    # Remap requests
    removed = self.remove_requests(old_team)
    readded = 0
    skipped = 0
    for r in removed:
        new_a = new_team if r.team_a == old_team else r.team_a
        new_b = new_team if r.team_b == old_team else r.team_b
        if self.has_duplicate_request(new_a, new_b):
            skipped += 1
        else:
            self.add_request(new_a, new_b)
            readded += 1

    self.last_result = None
    return {"removed": len(removed), "readded": readded, "skipped": skipped}
```

**Step 4: Run tests to verify they pass**
```bash
make test-local
# Expected: all tests pass
```

**Step 5: Commit**
```bash
git add bot/state.py bot/tests/test_state.py
git commit -m "Add GuildState.rename_team with conf schedule clear, request remapping, and last_result null"
```

---

## Task 5: Add `fmt_request_removed` formatter

**Files:**
- Modify: `bot/formatting.py`
- Modify: `bot/tests/test_formatting.py`

**Step 1: Write the failing tests**

Add to `bot/tests/test_formatting.py` (add `fmt_request_removed` to the import):

```python
class TestFmtRequestRemoved:
    def test_contains_both_team_names(self):
        result = fmt_request_removed("Alabama", "Auburn")
        assert "Alabama" in result
        assert "Auburn" in result

    def test_indicates_removal(self):
        result = fmt_request_removed("Alabama", "Auburn")
        assert "removed" in result.lower() or "deleted" in result.lower()
```

**Step 2: Run tests to verify they fail**
```bash
make test-local
# Expected: ImportError or AttributeError on fmt_request_removed
```

**Step 3: Implement `fmt_request_removed` in `bot/formatting.py`**

Add after `fmt_request_added`:

```python
def fmt_request_removed(team1: str, team2: str) -> str:
    """Response for a successful /request remove command."""
    return f"Request removed: {team1} vs. {team2}."
```

**Step 4: Run tests to verify they pass**
```bash
make test-local
```

**Step 5: Commit**
```bash
git add bot/formatting.py bot/tests/test_formatting.py
git commit -m "Add fmt_request_removed formatter"
```

---

## Task 6: Add `/request remove` command

**Files:**
- Modify: `bot/commands/request.py`

Add a `remove` subcommand to the existing `/request` group. It validates both teams, checks the request exists, removes it, sets `last_result = None`, and responds with `fmt_request_removed`.

**Step 1: Add the subcommand**

In `bot/commands/request.py`, add to the imports:
```python
from bot.formatting import fmt_request_added, fmt_request_removed
```

Then add this subcommand after `request_add` (before `tree.add_command`):

```python
    @request_group.command(
        name="remove", description="Remove a non-conference game request between two teams."
    )
    @app_commands.describe(
        team1="First team.",
        team2="Second team.",
    )
    async def request_remove(
        interaction: discord.Interaction, team1: str, team2: str
    ) -> None:
        if not await bot_ref.check_admin(interaction):
            return

        log.debug(
            "Guild %d: /request remove — user=%s team1=%r team2=%r",
            interaction.guild_id, interaction.user, team1, team2,
        )

        errors: list[str] = []
        if team1 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team1}.")
        if team2 not in bot_ref.valid_teams:
            errors.append(f"Unknown team: {team2}.")
        if errors:
            await interaction.response.send_message("\n".join(errors), ephemeral=True)
            return

        state = bot_ref.get_guild_state(interaction.guild_id)
        found = state.remove_request(team1, team2)
        if not found:
            await interaction.response.send_message(
                f"No request between {team1} and {team2} exists.", ephemeral=True
            )
            return

        state.last_result = None
        log.info(
            "Guild %d: /request remove — %s vs %s (user=%s)",
            interaction.guild_id, team1, team2, interaction.user,
        )
        msg = fmt_request_removed(team1, team2)
        if bot_ref.admin_warning(interaction.guild_id):
            msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg
        await interaction.response.send_message(msg)

    @request_remove.autocomplete("team1")
    @request_remove.autocomplete("team2")
    async def remove_team_autocomplete(
        interaction: discord.Interaction, current: str
    ) -> list[app_commands.Choice[str]]:
        matches = [
            app_commands.Choice(name=t, value=t)
            for t in sorted(bot_ref.valid_teams)
            if current.lower() in t.lower()
        ]
        return matches[:25]
```

**Step 2: Run tests to verify nothing broke**
```bash
make test-local
# Expected: all tests pass (no new tests for the thin handler itself)
```

**Step 3: Commit**
```bash
git add bot/commands/request.py
git commit -m "Add /request remove command"
```

---

## Task 7: Extract `_process_member` pure helper

**Files:**
- Modify: `bot/main.py`
- Modify: `bot/tests/test_parsing.py` (or create `bot/tests/test_main.py`)

Extract the per-member parsing logic from `_scrape_members` into a standalone function so it can be tested and reused by `on_member_update`.

The extracted function takes primitive values (no Discord objects) and returns a `ResolvedMember | UnresolvedMember`.

**Step 1: Write the failing tests**

Create `bot/tests/test_main.py`:

```python
"""Tests for pure helper functions extracted from bot/main.py."""

import pytest

from bot.main import ResolvedMember, UnresolvedMember, process_member_display_name


VALID_TEAMS = {"Alabama", "Auburn", "Georgia", "Notre Dame"}
NAME_REGEX = r"^(?P<team>.+)$"
IGNORE_REGEX = r"inactive"


class TestProcessMemberDisplayName:
    def test_resolved(self):
        result = process_member_display_name(
            display_name="Alabama",
            user_id=1,
            name_regex=NAME_REGEX,
            ignore_regex=IGNORE_REGEX,
            valid_teams=VALID_TEAMS,
        )
        assert isinstance(result, ResolvedMember)
        assert result.team == "Alabama"
        assert result.user_id == 1
        assert result.display_name == "Alabama"

    def test_unresolved_unparsable(self):
        result = process_member_display_name(
            display_name="not a team",
            user_id=2,
            name_regex=NAME_REGEX,
            ignore_regex=IGNORE_REGEX,
            valid_teams=VALID_TEAMS,
        )
        assert isinstance(result, UnresolvedMember)
        assert result.is_ignored is False
        assert result.user_id == 2

    def test_ignored(self):
        result = process_member_display_name(
            display_name="inactive | Alabama",
            user_id=3,
            name_regex=NAME_REGEX,
            ignore_regex=IGNORE_REGEX,
            valid_teams=VALID_TEAMS,
        )
        assert isinstance(result, UnresolvedMember)
        assert result.is_ignored is True

    def test_regex_with_team_group(self):
        result = process_member_display_name(
            display_name="Josh | Alabama",
            user_id=4,
            name_regex=r"^\w+ \| (?P<team>.+)$",
            ignore_regex=IGNORE_REGEX,
            valid_teams=VALID_TEAMS,
        )
        assert isinstance(result, ResolvedMember)
        assert result.team == "Alabama"
```

**Step 2: Run tests to verify they fail**
```bash
make test-local
# Expected: ImportError — process_member_display_name not yet defined
```

**Step 3: Refactor `_scrape_members` to use `process_member_display_name`**

In `bot/main.py`, add a module-level function (before `CFBBot`):

```python
def process_member_display_name(
    *,
    display_name: str,
    user_id: int,
    name_regex: str,
    ignore_regex: str,
    valid_teams: set[str],
) -> ResolvedMember | UnresolvedMember:
    """Parse one member's display name and return a resolved or unresolved result.

    Pure function — no Discord dependency. Testable independently.
    """
    try:
        team_name, is_ignored = parse_display_name(
            display_name, name_regex, ignore_regex, valid_teams
        )
    except ValueError:
        return UnresolvedMember(display_name, user_id, is_ignored=False)

    if is_ignored:
        return UnresolvedMember(display_name, user_id, is_ignored=True)
    if team_name is None:
        return UnresolvedMember(display_name, user_id, is_ignored=False)
    return ResolvedMember(display_name, team_name, user_id)
```

Then update `_scrape_members` to call it. Replace the `try/except` block inside the `async for` loop:

```python
        result = process_member_display_name(
            display_name=member.display_name,
            user_id=member.id,
            name_regex=name_regex,
            ignore_regex=ignore_regex,
            valid_teams=self.valid_teams,
        )
        if isinstance(result, UnresolvedMember):
            if result.is_ignored:
                log.debug("  ignored:    %s", member.display_name)
            else:
                log.debug("  unresolved: %s", member.display_name)
            unresolved.append(result)
        else:
            log.debug("  resolved:   %s → %s", member.display_name, result.team)
            human_teams[result.team] = result.user_id
            resolved.append(result)
```

Also remove the now-dead `return` inside the `try/except` error branch — the new helper handles `ValueError` gracefully by returning `UnresolvedMember`. However, you should preserve the original error log for malformed `name_regex`. Update the helper to re-raise `ValueError` from bad regex (it already does via `parse_display_name`), and in `_scrape_members` catch it at the guild level:

```python
        try:
            result = process_member_display_name(
                display_name=member.display_name,
                user_id=member.id,
                name_regex=name_regex,
                ignore_regex=ignore_regex,
                valid_teams=self.valid_teams,
            )
        except ValueError as exc:
            log.error("Guild %d: %s — check members.name_regex in config", guild.id, exc)
            return
```

**Step 4: Run tests to verify they pass**
```bash
make test-local
# Expected: all tests pass including the 4 new ones
```

**Step 5: Commit**
```bash
git add bot/main.py bot/tests/test_main.py
git commit -m "Extract process_member_display_name pure helper from _scrape_members"
```

---

## Task 8: Add `on_member_update` event handler

**Files:**
- Modify: `bot/main.py`
- Modify: `bot/tests/test_main.py`

**Step 1: Write the failing tests**

These tests call a new method `_handle_member_display_name_change` on `CFBBot` — a thin synchronous helper (no async, no Discord API calls) that takes before/after processed results plus guild state and updates all data structures. This keeps the logic testable without mocking Discord.

Add to `bot/tests/test_main.py`. You'll need these imports:

```python
from solver.model import Request, SolverResult
from bot.state import GuildState
from bot.main import CFBBot, ResolvedMember, UnresolvedMember, process_member_display_name


def _mock_result() -> SolverResult:
    return SolverResult(assignments=[], unscheduled=[])


def _make_resolved(display_name: str, team: str, user_id: int) -> ResolvedMember:
    return ResolvedMember(display_name=display_name, team=team, user_id=user_id)


def _make_unresolved(display_name: str, user_id: int, is_ignored: bool = False) -> UnresolvedMember:
    return UnresolvedMember(display_name=display_name, user_id=user_id, is_ignored=is_ignored)
```

Then add the permutation tests. For each permutation, assert every affected data structure:

```python
class TestHandleMemberDisplayNameChange:
    GUILD_ID = 100
    USER_ID = 42

    def _make_bot_state(self):
        """Set up bot state with Alabama resolved for USER_ID."""
        # We can't instantiate CFBBot (needs Discord token), so test the helper directly.
        # The helper is a standalone function, not a method.
        pass  # See Step 3 — we'll test via module-level helper

    # --- Permutation 1: resolved → resolved (same team, no-op) ---
    def test_resolved_to_same_resolved_no_op(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=2)
        state.add_request("Alabama", "Notre Dame")
        state.last_result = _mock_result()

        human_teams = {"Alabama": self.USER_ID}
        resolved = [_make_resolved("Alabama", "Alabama", self.USER_ID)]
        unresolved = []

        before = _make_resolved("Alabama", "Alabama", self.USER_ID)
        after = _make_resolved("Alabama", "Alabama", self.USER_ID)

        handle_member_display_name_change(
            guild_id=self.GUILD_ID,
            before=before,
            after=after,
            state=state,
            human_teams=human_teams,
            resolved=resolved,
            unresolved=unresolved,
        )

        # No change expected
        assert human_teams == {"Alabama": self.USER_ID}
        assert len(resolved) == 1
        assert resolved[0].team == "Alabama"
        assert unresolved == []
        assert "Alabama" in state.conference_schedules
        assert len(state.requests) == 1
        assert state.last_result is None  # rename_team always nulls it

    # --- Permutation 2: resolved → resolved (different team, full rename) ---
    def test_resolved_to_different_resolved(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=2)
        state.add_request("Alabama", "Notre Dame")
        state.last_result = _mock_result()

        human_teams = {"Alabama": self.USER_ID}
        resolved = [_make_resolved("old display", "Alabama", self.USER_ID)]
        unresolved = []

        before = _make_resolved("old display", "Alabama", self.USER_ID)
        after = _make_resolved("new display", "Auburn", self.USER_ID)

        handle_member_display_name_change(
            guild_id=self.GUILD_ID,
            before=before,
            after=after,
            state=state,
            human_teams=human_teams,
            resolved=resolved,
            unresolved=unresolved,
        )

        # human_teams updated
        assert "Alabama" not in human_teams
        assert human_teams.get("Auburn") == self.USER_ID

        # resolved list updated
        assert len(resolved) == 1
        assert resolved[0].team == "Auburn"
        assert resolved[0].display_name == "new display"
        assert unresolved == []

        # conf schedule cleared for Alabama, not Auburn
        assert "Alabama" not in state.conference_schedules
        assert "Alabama" not in state.conference_home_games

        # request remapped to Auburn
        assert len(state.requests) == 1
        pair = {state.requests[0].team_a, state.requests[0].team_b}
        assert pair == {"Auburn", "Notre Dame"}

        # last_result nulled
        assert state.last_result is None

    # --- Permutation 3: resolved → unresolved ---
    def test_resolved_to_unresolved(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=2)
        state.add_request("Alabama", "Notre Dame")
        state.last_result = _mock_result()

        human_teams = {"Alabama": self.USER_ID}
        resolved = [_make_resolved("old display", "Alabama", self.USER_ID)]
        unresolved = []

        before = _make_resolved("old display", "Alabama", self.USER_ID)
        after = _make_unresolved("???", self.USER_ID)

        handle_member_display_name_change(
            guild_id=self.GUILD_ID,
            before=before,
            after=after,
            state=state,
            human_teams=human_teams,
            resolved=resolved,
            unresolved=unresolved,
        )

        # removed from human_teams and resolved, added to unresolved
        assert "Alabama" not in human_teams
        assert resolved == []
        assert len(unresolved) == 1
        assert unresolved[0].user_id == self.USER_ID

        # conf schedule cleared
        assert "Alabama" not in state.conference_schedules
        assert "Alabama" not in state.conference_home_games

        # requests dropped
        assert len(state.requests) == 0

        # last_result nulled
        assert state.last_result is None

    # --- Permutation 4: unresolved → resolved ---
    def test_unresolved_to_resolved(self):
        state = GuildState()
        state.add_request("Georgia", "LSU")
        state.last_result = _mock_result()

        human_teams = {"Georgia": 99}
        resolved = [_make_resolved("Georgia", "Georgia", 99)]
        unresolved = [_make_unresolved("???", self.USER_ID)]

        before = _make_unresolved("???", self.USER_ID)
        after = _make_resolved("Auburn", "Auburn", self.USER_ID)

        handle_member_display_name_change(
            guild_id=self.GUILD_ID,
            before=before,
            after=after,
            state=state,
            human_teams=human_teams,
            resolved=resolved,
            unresolved=unresolved,
        )

        # added to human_teams and resolved, removed from unresolved
        assert human_teams.get("Auburn") == self.USER_ID
        assert len(resolved) == 2
        assert any(r.team == "Auburn" for r in resolved)
        assert unresolved == []

        # no conf schedule changes (no old team to clear)
        assert "Georgia" in state.conference_schedules  # untouched

        # requests unchanged (no old team to remap)
        assert len(state.requests) == 1

        # last_result unchanged (no state change to scheduling data)
        assert state.last_result is not None

    # --- Permutation 5: unresolved → unresolved ---
    def test_unresolved_to_unresolved(self):
        state = GuildState()
        state.set_conference_schedule("Georgia", [1, 2], home_games=1)
        state.add_request("Georgia", "LSU")
        state.last_result = _mock_result()

        human_teams = {"Georgia": 99}
        resolved = [_make_resolved("Georgia", "Georgia", 99)]
        unresolved = [_make_unresolved("???", self.USER_ID)]

        before = _make_unresolved("???", self.USER_ID)
        after = _make_unresolved("still ???", self.USER_ID)

        handle_member_display_name_change(
            guild_id=self.GUILD_ID,
            before=before,
            after=after,
            state=state,
            human_teams=human_teams,
            resolved=resolved,
            unresolved=unresolved,
        )

        # display_name updated in unresolved
        assert len(unresolved) == 1
        assert unresolved[0].display_name == "still ???"
        assert unresolved[0].user_id == self.USER_ID

        # everything else untouched
        assert human_teams == {"Georgia": 99}
        assert len(resolved) == 1
        assert "Georgia" in state.conference_schedules
        assert len(state.requests) == 1
        assert state.last_result is not None
```

**Step 2: Run tests to verify they fail**
```bash
make test-local
# Expected: ImportError on handle_member_display_name_change
```

**Step 3: Implement `handle_member_display_name_change` and `on_member_update`**

In `bot/main.py`, add a module-level function (after `process_member_display_name`):

```python
def handle_member_display_name_change(
    *,
    guild_id: int,
    before: ResolvedMember | UnresolvedMember,
    after: ResolvedMember | UnresolvedMember,
    state: GuildState,
    human_teams: dict[str, int],
    resolved: list[ResolvedMember],
    unresolved: list[UnresolvedMember],
) -> None:
    """Apply a display name change to all in-memory state.

    Pure function (no Discord API calls). Testable independently.
    """
    # Remove old entry from whichever list they were in
    if isinstance(before, ResolvedMember):
        human_teams.pop(before.team, None)
        resolved[:] = [r for r in resolved if r.user_id != before.user_id]
    else:
        unresolved[:] = [u for u in unresolved if u.user_id != before.user_id]

    # Add new entry
    if isinstance(after, ResolvedMember):
        human_teams[after.team] = after.user_id
        resolved.append(after)
    else:
        unresolved.append(after)

    # Apply scheduling state changes
    if isinstance(before, ResolvedMember) and isinstance(after, ResolvedMember):
        # resolved → resolved: rename (even if same team — rename_team is idempotent)
        state.rename_team(before.team, after.team)
    elif isinstance(before, ResolvedMember) and isinstance(after, UnresolvedMember):
        # resolved → unresolved: drop schedule and requests
        state.conference_schedules.pop(before.team, None)
        state.conference_home_games.pop(before.team, None)
        state.remove_requests(before.team)
        state.last_result = None
    # unresolved → resolved or unresolved → unresolved: no scheduling state to change
```

Then add `on_member_update` to `CFBBot`:

```python
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if before.display_name == after.display_name:
            return

        guild_id = after.guild.id
        config = self._guild_configs.get(guild_id, {})
        name_regex: str = config.get("members", {}).get("name_regex", "^(?P<team>.+)$")
        ignore_regex: str = config.get("members", {}).get("ignore_regex", "inactive")

        try:
            before_result = process_member_display_name(
                display_name=before.display_name,
                user_id=before.id,
                name_regex=name_regex,
                ignore_regex=ignore_regex,
                valid_teams=self.valid_teams,
            )
            after_result = process_member_display_name(
                display_name=after.display_name,
                user_id=after.id,
                name_regex=name_regex,
                ignore_regex=ignore_regex,
                valid_teams=self.valid_teams,
            )
        except ValueError as exc:
            log.error("Guild %d: member update parse error: %s", guild_id, exc)
            return

        state = self.get_guild_state(guild_id)
        human_teams = self._human_teams.setdefault(guild_id, {})
        resolved = self._resolved.setdefault(guild_id, [])
        unresolved = self._unresolved.setdefault(guild_id, [])

        log.info(
            "Guild %d: member display name change: %r → %r (user_id=%d)",
            guild_id, before.display_name, after.display_name, after.id,
        )

        handle_member_display_name_change(
            guild_id=guild_id,
            before=before_result,
            after=after_result,
            state=state,
            human_teams=human_teams,
            resolved=resolved,
            unresolved=unresolved,
        )
```

Also update the imports in `bot/tests/test_main.py` to include `handle_member_display_name_change`.

**Step 4: Run tests to verify they pass**
```bash
make test-local
# Expected: all tests pass
```

**Step 5: Commit**
```bash
git add bot/main.py bot/tests/test_main.py
git commit -m "Add on_member_update handler with process_member_display_name and handle_member_display_name_change"
```

---

## Task 9: Run full test suite and merge

**Step 1: Run full test suite**
```bash
make test PROXY=http://host.docker.internal:3128
# Expected: all tests pass
```

**Step 2: Squash-merge to main**
```bash
git checkout main
git merge --squash feature/display-name-change
```

**Step 3: Update CHANGELOG.md**

Add an entry under `[Unreleased]` summarizing the feature:
- Add `on_member_update` handler: display name changes update team mapping, conf schedule, and requests automatically
- Add `/request remove` command
- Extract `process_member_display_name` pure helper

**Step 4: Commit the squash**
```bash
git add -A
git commit -m "Release X.Y.Z: display name change handling and /request remove"
```

**Step 5: Delete feature branch**
```bash
git branch -d feature/display-name-change
```
