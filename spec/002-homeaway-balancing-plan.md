# Feature 2: Home/Away Balancing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Extend the scheduler to assign a home team to every scheduled non-conference game, optimizing for per-team home/away balance across the full season.

**Architecture:** Two-pass approach — pass 1 (`solve()`) assigns weeks as before; pass 2 (`assign_home_away()`) runs a second CP-SAT model over the fixed assignments to assign home/away minimizing imbalance. `/conference_schedule` gains a required `home_games` integer param. Formatting updated to show `{away} at {home}` / `{home} vs. {away}` notation.

**Tech Stack:** Python 3.13, OR-Tools CP-SAT, discord.py, pytest

---

## Before You Start

Read these files to understand existing code:
- `solver/model.py` — Team, Request, Assignment, SolverInput, SolverResult dataclasses
- `solver/scheduler.py` — existing `solve()` function
- `solver/tests/test_scheduler.py` — existing solver tests (helper functions `human()`, `cpu()`, `req()`)
- `bot/state.py` — GuildState
- `bot/tests/test_state.py` — state tests
- `bot/formatting.py` — formatting functions
- `bot/tests/test_formatting.py` — formatting tests (helper `_assignment()`)
- `bot/commands/conf.py` — `/conference_schedule` command handler
- `bot/commands/schedule.py` — `/schedule create` command handler

Run tests before starting to confirm baseline passes:
```bash
make test-local
```
All 108 tests should pass.

---

## Task 1: Create feature branch

**Step 1: Create and switch to feature branch**
```bash
git checkout -b feature/homeaway-balancing
```

**Step 2: Verify you're on the right branch**
```bash
git branch --show-current
# Expected: feature/homeaway-balancing
```

---

## Task 2: Add `conference_home_games` to `Team`

**Files:**
- Modify: `solver/model.py`
- Modify: `solver/tests/test_scheduler.py` (update `human()` helper)

The `Team` dataclass needs a `conference_home_games` field. It must default to `0` so CPU teams work without it and existing tests don't break.

**Step 1: Write the failing test**

Add to `solver/tests/test_scheduler.py` inside `TestBasicScheduling` (or a new class at the bottom):

```python
class TestTeamModel:
    def test_conference_home_games_defaults_to_zero(self):
        team = Team(name="Alabama", conference_weeks=frozenset([1, 2, 3]))
        assert team.conference_home_games == 0

    def test_conference_home_games_stored(self):
        team = Team(name="Alabama", conference_weeks=frozenset([1, 2, 3]), conference_home_games=2)
        assert team.conference_home_games == 2
```

**Step 2: Run to confirm failure**
```bash
make test-local
# Expected: FAIL — "unexpected keyword argument 'conference_home_games'"
```

**Step 3: Add field to `Team` in `solver/model.py`**

In `solver/model.py`, add `conference_home_games: int = 0` after `is_cpu`:

```python
@dataclass(frozen=True)
class Team:
    name: str
    conference_weeks: frozenset[int] = field(default_factory=frozenset)
    is_cpu: bool = False
    conference_home_games: int = 0
```

**Step 4: Update the `human()` helper in `solver/tests/test_scheduler.py`**

The helper currently doesn't support `conference_home_games`. Update it so tests can pass it when needed:

```python
def human(name: str, conf_weeks: list[int] = [], conf_home: int = 0) -> Team:
    return Team(name=name, conference_weeks=frozenset(conf_weeks), is_cpu=False, conference_home_games=conf_home)
```

**Step 5: Run tests to confirm all pass**
```bash
make test-local
# Expected: all 108 tests pass (field has default, nothing breaks)
```

**Step 6: Commit**
```bash
git add solver/model.py solver/tests/test_scheduler.py
git commit -m "Add conference_home_games field to Team model"
```

---

## Task 3: Add `home_team` to `Assignment`

**Files:**
- Modify: `solver/model.py`

`Assignment` needs a `home_team: str` field. It must default to `""` so existing tests that construct `Assignment(request=..., week=...)` don't break. The empty string means "not yet assigned" — the bot always runs `assign_home_away()` before using home_team.

**Step 1: Write the failing test**

Add to `TestTeamModel` (or a new class) in `solver/tests/test_scheduler.py`:

```python
class TestAssignmentModel:
    def test_home_team_defaults_to_empty_string(self):
        r = Request(team_a="Alabama", team_b="Auburn")
        a = Assignment(request=r, week=3)
        assert a.home_team == ""

    def test_home_team_stored(self):
        r = Request(team_a="Alabama", team_b="Auburn")
        a = Assignment(request=r, week=3, home_team="Alabama")
        assert a.home_team == "Alabama"
```

**Step 2: Run to confirm failure**
```bash
make test-local
# Expected: FAIL — "unexpected keyword argument 'home_team'"
```

**Step 3: Add field to `Assignment` in `solver/model.py`**

```python
@dataclass(frozen=True)
class Assignment:
    request: Request
    week: int
    home_team: str = ""
```

**Step 4: Run tests to confirm all pass**
```bash
make test-local
# Expected: all tests pass (field has default, nothing breaks)
```

**Step 5: Commit**
```bash
git add solver/model.py solver/tests/test_scheduler.py
git commit -m "Add home_team field to Assignment model"
```

---

## Task 4: Update formatting for home/away notation

**Files:**
- Modify: `bot/formatting.py`
- Modify: `bot/tests/test_formatting.py`

Convention: `{home} vs. {away}` when the listed team is home; `{away} at {home}` when the listed team is away. This applies to both `fmt_schedule_result` (full results) and `fmt_schedule_show` (per-team view).

**Step 1: Update the `_assignment` helper in `bot/tests/test_formatting.py`**

The helper currently doesn't support `home_team`. Update it:

```python
def _assignment(a: str, b: str, week: int, home_team: str = "") -> Assignment:
    return Assignment(request=_req(a, b), week=week, home_team=home_team)
```

**Step 2: Write failing tests for the new formatting**

Add a new test class to `bot/tests/test_formatting.py`:

```python
class TestFmtScheduleResultHomeAway:
    def test_home_team_shown_with_vs(self):
        # Alabama is home → "Alabama vs. Auburn"
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3, home_team="Alabama")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result)
        assert "Alabama vs. Auburn" in text

    def test_away_team_shown_with_at(self):
        # Auburn is home → "Alabama at Auburn"
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3, home_team="Auburn")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result)
        assert "Alabama at Auburn" in text


class TestFmtScheduleShowHomeAway:
    def test_team_home_shows_vs(self):
        # Alabama is home → "vs. Auburn"
        a = _assignment("Alabama", "Auburn", 3, home_team="Alabama")
        text = fmt_schedule_show("Alabama", [a])
        assert "vs. Auburn" in text
        assert "at" not in text

    def test_team_away_shows_at(self):
        # Auburn is home → Alabama is at Auburn
        a = _assignment("Alabama", "Auburn", 3, home_team="Auburn")
        text = fmt_schedule_show("Alabama", [a])
        assert "at Auburn" in text
        assert "vs." not in text
```

**Step 3: Run to confirm failures**
```bash
make test-local
# Expected: new tests FAIL (formatting still shows "vs." unconditionally)
```

**Step 4: Update `fmt_schedule_result` in `bot/formatting.py`**

Replace the game line generation inside `fmt_schedule_result`:

```python
for a in sorted_assignments:
    home = a.home_team if a.home_team else a.request.team_a
    away = a.request.team_b if home == a.request.team_a else a.request.team_a
    lines.append(f"  Week {a.week}: {home} vs. {away}" if home == a.request.team_a
                 else f"  Week {a.week}: {away} at {home}")
```

Wait — that's needlessly convoluted. Here's the clean version:

```python
for a in sorted_assignments:
    if a.home_team and a.home_team == a.request.team_b:
        # team_b is home: show "team_a at team_b"
        lines.append(f"  Week {a.week}: {a.request.team_a} at {a.request.team_b}")
    else:
        # team_a is home (or home_team not set): show "team_a vs. team_b"
        lines.append(f"  Week {a.week}: {a.request.team_a} vs. {a.request.team_b}")
```

**Step 5: Update `fmt_schedule_show` in `bot/formatting.py`**

Replace the game line generation inside `fmt_schedule_show`:

```python
for a in sorted_assignments:
    opponent = a.request.team_b if a.request.team_a == team else a.request.team_a
    if a.home_team == team:
        lines.append(f"  Week {a.week}: vs. {opponent}")
    elif a.home_team == opponent:
        lines.append(f"  Week {a.week}: at {opponent}")
    else:
        # home_team not set — fall back to neutral display
        lines.append(f"  Week {a.week}: vs. {opponent}")
```

**Step 6: Update existing formatting tests that checked the old output**

In `bot/tests/test_formatting.py`, find `TestFmtScheduleResult.test_fulfilled_game_listed` and `TestFmtScheduleShow`. These used `_assignment()` without `home_team`, so `home_team=""` and the new code falls back to `vs.` — they should still pass. Run to verify.

**Step 7: Run tests to confirm all pass**
```bash
make test-local
# Expected: all tests pass
```

**Step 8: Commit**
```bash
git add bot/formatting.py bot/tests/test_formatting.py
git commit -m "Update schedule formatting for home/away vs./at notation"
```

---

## Task 5: Implement `assign_home_away()`

**Files:**
- Modify: `solver/scheduler.py`
- Create: `solver/tests/test_home_away.py`

This function takes a fixed list of `Assignment` objects (with `home_team=""`) and a `teams` dict, then returns new `Assignment` objects with `home_team` set to minimize per-team home/away imbalance.

**Math background:**
For each human team T:
- `total_home(T)` = `conference_home_games(T)` + NC home games assigned to T
- `total_games(T)` = `len(conference_weeks(T))` + NC games involving T
- `imbalance(T)` = `|2 * total_home(T) - total_games(T)|`

The solver minimizes `sum(imbalance(T))` over all human teams. CPU teams are excluded from the objective — for games involving a CPU team, the solver still picks home/away but only the human team's balance matters.

**Decision variable:** `h[i]` = 1 if `team_a` of assignment `i` is the home team.

**NC home count for team T:**
- Games where T is `team_a`: `h[i]` contributes to T's home count when True
- Games where T is `team_b`: `h[i]` = False means T is home, i.e., `(1 - h[i])` contributes

Using `LinearExpr.weighted_sum`, we can express this as:
```
nc_home_expr = weighted_sum(
    [h[i] for team_a games] + [h[i] for team_b games],
    [+1, ..., -1, ...]
) + len(team_b_games)
```
i.e. `effective_conf_home = conference_home_games + len(team_b_games)`, and the expression is a weighted sum with +1 for team_a indices, -1 for team_b indices.

**Step 1: Write failing tests**

Create `solver/tests/test_home_away.py`:

```python
"""Tests for assign_home_away()."""
import dataclasses
import pytest

from solver.model import Assignment, Request, Team
from solver.scheduler import assign_home_away


def human(name: str, conf_weeks: list[int] = [], conf_home: int = 0) -> Team:
    return Team(name=name, conference_weeks=frozenset(conf_weeks), is_cpu=False, conference_home_games=conf_home)


def cpu(name: str) -> Team:
    return Team(name=name, is_cpu=True)


def assignment(a: str, b: str, week: int) -> Assignment:
    return Assignment(request=Request(team_a=a, team_b=b), week=week)


class TestAssignHomeAwayEmpty:
    def test_empty_list_returns_empty(self):
        result = assign_home_away([], {})
        assert result == []


class TestAssignHomeAwayBasic:
    def test_home_team_is_set(self):
        teams = {
            "Alabama": human("Alabama", conf_weeks=[1, 2, 3, 4], conf_home=2),
            "Auburn": human("Auburn", conf_weeks=[5, 6, 7, 8], conf_home=2),
        }
        assignments = [assignment("Alabama", "Auburn", week=9)]
        result = assign_home_away(assignments, teams)
        assert len(result) == 1
        assert result[0].home_team in ("Alabama", "Auburn")

    def test_returns_new_assignment_objects(self):
        # Assignment is frozen — assign_home_away must return new objects
        teams = {
            "Alabama": human("Alabama", conf_weeks=[1, 2], conf_home=1),
            "Auburn": human("Auburn", conf_weeks=[3, 4], conf_home=1),
        }
        a = assignment("Alabama", "Auburn", week=5)
        result = assign_home_away([a], teams)
        assert result[0] is not a

    def test_week_and_request_preserved(self):
        teams = {
            "Alabama": human("Alabama", conf_weeks=[1], conf_home=0),
            "Auburn": human("Auburn", conf_weeks=[2], conf_home=0),
        }
        a = assignment("Alabama", "Auburn", week=7)
        result = assign_home_away([a], teams)
        assert result[0].week == 7
        assert result[0].request.team_a == "Alabama"
        assert result[0].request.team_b == "Auburn"


class TestAssignHomeAwayBalance:
    def test_prefers_home_for_away_heavy_team(self):
        # Alabama: 4 conf games, 0 home → very away-heavy → should be home in NC game
        # Auburn: 4 conf games, 4 home → very home-heavy → should be away in NC game
        teams = {
            "Alabama": human("Alabama", conf_weeks=[1, 2, 3, 4], conf_home=0),
            "Auburn": human("Auburn", conf_weeks=[5, 6, 7, 8], conf_home=4),
        }
        result = assign_home_away([assignment("Alabama", "Auburn", 9)], teams)
        assert result[0].home_team == "Alabama"

    def test_achieves_perfect_balance_when_possible(self):
        # Alabama: 4 conf games, 2 home → balanced in conf
        # Two NC games: Alabama should go 1H 1A to stay balanced
        teams = {
            "Alabama": human("Alabama", conf_weeks=[1, 2, 3, 4], conf_home=2),
            "TCU": human("TCU", conf_weeks=[5, 6, 7, 8], conf_home=2),
            "Clemson": human("Clemson", conf_weeks=[9, 10, 11, 12], conf_home=2),
        }
        assignments = [
            assignment("Alabama", "TCU", week=13),
            assignment("Alabama", "Clemson", week=14),
        ]
        result = assign_home_away(assignments, teams)
        alabama_home_count = sum(1 for a in result if a.home_team == "Alabama")
        assert alabama_home_count == 1

    def test_cpu_opponent_does_not_affect_balance_objective(self):
        # Alabama: 4 conf games, 4 home → home-heavy → should be AWAY against CPU
        # CPU team has no balance objective
        teams = {
            "Alabama": human("Alabama", conf_weeks=[1, 2, 3, 4], conf_home=4),
            "CPU Team": cpu("CPU Team"),
        }
        result = assign_home_away([assignment("Alabama", "CPU Team", 5)], teams)
        # Alabama is home-heavy, so it should be away → CPU Team is home
        assert result[0].home_team == "CPU Team"

    def test_minimizes_total_imbalance_across_teams(self):
        # Alabama: 4H 4A in conf → balanced. 1 NC game.
        # Auburn: 6H 2A in conf → home-heavy. 1 NC game (vs Alabama).
        # Best: Auburn away → Alabama home → Alabama becomes 5H 4A (imbalance 1)
        #       Auburn becomes 6H 3A (imbalance 3). Total = 4.
        # Alt:  Auburn home → Alabama away → Alabama 4H 5A (imbalance 1)
        #       Auburn 7H 2A (imbalance 5). Total = 6.
        # So Alabama should be home.
        teams = {
            "Alabama": human("Alabama", conf_weeks=[1, 2, 3, 4, 5, 6, 7, 8], conf_home=4),
            "Auburn": human("Auburn", conf_weeks=[1, 2, 3, 4, 5, 6, 7, 8], conf_home=6),
        }
        result = assign_home_away([assignment("Alabama", "Auburn", 9)], teams)
        assert result[0].home_team == "Alabama"


class TestAssignHomeAwayCPUOnly:
    def test_all_cpu_game_sets_some_home_team(self):
        # Both teams are CPU — any valid assignment is fine, just check it runs
        teams = {
            "CPU A": cpu("CPU A"),
            "CPU B": cpu("CPU B"),
        }
        result = assign_home_away([assignment("CPU A", "CPU B", 3)], teams)
        assert result[0].home_team in ("CPU A", "CPU B")
```

**Step 2: Run to confirm failure**
```bash
make test-local
# Expected: FAIL — "cannot import name 'assign_home_away'"
```

**Step 3: Implement `assign_home_away` in `solver/scheduler.py`**

Add at the top of the file:
```python
import dataclasses
from ortools.sat.python import cp_model
```
(Note: `cp_model` is already imported. Just add `import dataclasses`.)

Add after the `solve()` function:

```python
def assign_home_away(
    assignments: list[Assignment],
    teams: dict[str, Team],
) -> list[Assignment]:
    """
    Assign a home team to each scheduled game to minimize per-team home/away imbalance.

    Decision variable h[i] = 1 means team_a of assignments[i] is home.

    For each human team T, computes:
        total_home(T) = conference_home_games(T) + NC home games assigned to T
        imbalance(T) = |2 * total_home(T) - total_games(T)|

    CPU teams are excluded from the objective (their games are assigned to benefit
    the human opponent's balance).

    Returns new Assignment objects (Assignment is frozen) with home_team set.
    """
    if not assignments:
        return []

    model = cp_model.CpModel()

    # h[i] = 1 → team_a of assignments[i] is home
    h = [model.new_bool_var(f"h_{i}") for i in range(len(assignments))]

    dev_vars = []

    for team_name, team in teams.items():
        if team.is_cpu:
            continue

        # Find assignment indices where this team is team_a or team_b
        team_a_idxs = [i for i, a in enumerate(assignments) if a.request.team_a == team_name]
        team_b_idxs = [i for i, a in enumerate(assignments) if a.request.team_b == team_name]
        nc_total = len(team_a_idxs) + len(team_b_idxs)

        if nc_total == 0:
            continue  # Team has no NC games scheduled — skip

        # NC home expression:
        #   team_a games: h[i] contributes +1 when team is home (h[i]=1)
        #   team_b games: h[i] contributes -1 (when h[i]=1, team is AWAY)
        # nc_home = weighted_sum + len(team_b_idxs)
        # Absorb the constant into effective_conf_home:
        effective_conf_home = team.conference_home_games + len(team_b_idxs)

        vars_list = [h[i] for i in team_a_idxs] + [h[i] for i in team_b_idxs]
        weights = [1] * len(team_a_idxs) + [-1] * len(team_b_idxs)

        nc_home_expr = cp_model.LinearExpr.weighted_sum(vars_list, weights)
        # total_home = effective_conf_home + nc_home_expr
        # total_games = len(conference_weeks) + nc_total (constant)
        total_games = len(team.conference_weeks) + nc_total

        # imbalance = |2 * total_home - total_games|
        # Linearize: dev >= 2*total_home - total_games AND dev >= total_games - 2*total_home
        dev = model.new_int_var(0, total_games, f"dev_{team_name}")
        model.add(dev >= 2 * effective_conf_home + 2 * nc_home_expr - total_games)
        model.add(dev >= total_games - 2 * effective_conf_home - 2 * nc_home_expr)
        dev_vars.append(dev)

    if dev_vars:
        model.minimize(cp_model.LinearExpr.sum(dev_vars))

    solver = cp_model.CpSolver()
    solver.solve(model)

    return [
        dataclasses.replace(
            a,
            home_team=a.request.team_a if solver.boolean_value(h[i]) else a.request.team_b,
        )
        for i, a in enumerate(assignments)
    ]
```

**Step 4: Run tests to confirm all pass**
```bash
make test-local
# Expected: all tests pass (including new home/away tests)
```

**Step 5: Commit**
```bash
git add solver/scheduler.py solver/tests/test_home_away.py
git commit -m "Implement assign_home_away() CP-SAT solver pass"
```

---

## Task 6: Add `conference_home_games` storage to `GuildState`

**Files:**
- Modify: `bot/state.py`
- Modify: `bot/tests/test_state.py`

`GuildState.set_conference_schedule` gains a required `home_games: int` parameter. A new `conference_home_games: dict[str, int]` field stores the values. The existing `conference_schedules` dict (weeks only) is unchanged.

**Step 1: Write the failing test**

Add a new test class to `bot/tests/test_state.py`:

```python
class TestSetConferenceScheduleHomeGames:
    def test_home_games_stored(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5], home_games=3)
        assert state.conference_home_games["Alabama"] == 3

    def test_home_games_updated_on_replace(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5], home_games=3)
        state.set_conference_schedule("Alabama", [2, 4, 6], home_games=2)
        assert state.conference_home_games["Alabama"] == 2

    def test_home_games_stored_independently_per_team(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=1)
        state.set_conference_schedule("Auburn", [5, 7], home_games=2)
        assert state.conference_home_games["Alabama"] == 1
        assert state.conference_home_games["Auburn"] == 2
```

**Step 2: Run to confirm failure**
```bash
make test-local
# Expected: FAIL — set_conference_schedule() got unexpected keyword argument 'home_games'
```

**Step 3: Update `GuildState` in `bot/state.py`**

```python
@dataclass
class GuildState:
    """All mutable scheduling state for one Discord guild."""

    conference_schedules: dict[str, set[int]] = field(default_factory=dict)
    conference_home_games: dict[str, int] = field(default_factory=dict)
    requests: list[Request] = field(default_factory=list)
    last_result: SolverResult | None = None

    def set_conference_schedule(self, team: str, weeks: list[int], home_games: int) -> bool:
        """Store or replace a team's conference schedule.

        Returns True if a prior entry was replaced, False if this is a new entry.
        """
        existed = team in self.conference_schedules
        self.conference_schedules[team] = set(weeks)
        self.conference_home_games[team] = home_games
        return existed
```

**Step 4: Fix all callers of `set_conference_schedule` in existing tests**

In `bot/tests/test_state.py`, every call to `set_conference_schedule` that uses only 2 args will now fail. Update them all to pass `home_games=0` (a neutral value that doesn't affect the tested behavior):

```python
# Example — find every occurrence and add home_games=0:
state.set_conference_schedule("Alabama", [1, 3, 5], home_games=0)
state.set_conference_schedule("Auburn", [2], home_games=0)
# etc.
```

Search for all occurrences: `grep -n "set_conference_schedule" bot/tests/test_state.py`

**Step 5: Run tests to confirm all pass**
```bash
make test-local
```

**Step 6: Commit**
```bash
git add bot/state.py bot/tests/test_state.py
git commit -m "Store conference_home_games in GuildState"
```

---

## Task 7: Add `home_games` parameter to `/conference_schedule` command

**Files:**
- Modify: `bot/commands/conf.py`

The Discord slash command gains a required `home_games: int` parameter. The handler passes it to `state.set_conference_schedule`. No new pure function needed — the parsing is just Discord's native integer handling.

Also update the confirmation message formatter to echo home_games back to the admin.

**Step 1: Update `bot/formatting.py` — add `home_games` to `fmt_conf_schedule_set`**

First write a failing test in `bot/tests/test_formatting.py`:

```python
class TestFmtConfScheduleSetHomeGames:
    def test_home_games_shown_in_confirmation(self):
        result = fmt_conf_schedule_set("Alabama", [1, 3, 5], home_games=3, updated=False)
        assert "3 home" in result
```

Run: `make test-local` → FAIL

Update `fmt_conf_schedule_set` in `bot/formatting.py` to accept and display `home_games`:

```python
def fmt_conf_schedule_set(team: str, weeks: list[int], *, home_games: int, updated: bool) -> str:
    """Response for a successful /conference_schedule command."""
    verb = "Updated" if updated else "Set"
    weeks_str = " ".join(str(w) for w in sorted(weeks))
    return (
        f"{verb} conference schedule for {team}.\n"
        f"{team}: conference games on weeks {weeks_str} ({home_games} home)."
    )
```

Update existing `fmt_conf_schedule_set` tests to pass `home_games=0` (or any int):
```python
fmt_conf_schedule_set("Alabama", [1, 3, 5], home_games=0, updated=False)
```

Run: `make test-local` → all pass.

**Step 2: Update `bot/commands/conf.py`**

Add `home_games: int` as a Discord command parameter and wire it through:

```python
@tree.command(
    name="conference_schedule",
    description="Enter a team's conference schedule for the current season.",
)
@app_commands.describe(
    team="The team whose schedule is being entered (from the official team list).",
    weeks="Space-separated week numbers (1–14) with conference games. E.g. '1 3 5 7 9 11'.",
    home_games="Number of home games among those conference weeks.",
)
async def conference_schedule(
    interaction: discord.Interaction, team: str, weeks: str, home_games: int
) -> None:
    if not await bot_ref.check_admin(interaction):
        return

    if team not in bot_ref.valid_teams:
        await interaction.response.send_message(
            f"Unknown team: {team}. Team must be from the official team list.",
            ephemeral=True,
        )
        return

    try:
        week_list = parse_conf_weeks(weeks)
    except ValueError as e:
        await interaction.response.send_message(str(e), ephemeral=True)
        return

    state = bot_ref.get_guild_state(interaction.guild_id)
    updated = state.set_conference_schedule(team, week_list, home_games=home_games)

    msg = fmt_conf_schedule_set(team, week_list, home_games=home_games, updated=updated)
    if bot_ref.admin_warning(interaction.guild_id):
        msg = bot_ref.admin_warning(interaction.guild_id) + "\n\n" + msg

    await interaction.response.send_message(msg)
```

**Step 3: Run tests to confirm all pass**
```bash
make test-local
```

**Step 4: Commit**
```bash
git add bot/commands/conf.py bot/formatting.py bot/tests/test_formatting.py
git commit -m "Add home_games param to /conference_schedule; show in confirmation"
```

---

## Task 8: Wire `assign_home_away` into `/schedule create`

**Files:**
- Modify: `bot/commands/schedule.py`

`/schedule create` must now:
1. Build `Team` objects with `conference_home_games` from `state.conference_home_games`
2. Call `assign_home_away(result.assignments, teams)` after `solve()`
3. Store the home-away-enriched assignments in `state.last_result`

**Step 1: Update `bot/commands/schedule.py`**

Add import at top:
```python
from solver.scheduler import assign_home_away, solve
```

Update the `schedule_create` handler — specifically the block that builds teams and calls solve:

```python
# Build solver input
teams: dict[str, Team] = {}
for team_name, weeks in state.conference_schedules.items():
    teams[team_name] = Team(
        name=team_name,
        conference_weeks=frozenset(weeks),
        is_cpu=False,
        conference_home_games=state.conference_home_games.get(team_name, 0),
    )

solver_input = SolverInput(teams=teams, requests=state.requests)
result = solve(solver_input)

# Assign home/away for all scheduled games
assigned = assign_home_away(result.assignments, teams)
result = SolverResult(assignments=assigned, unscheduled=result.unscheduled)

state.last_result = result
```

Note: `SolverResult` is already imported. No new imports needed beyond `assign_home_away`.

**Step 2: Run tests to confirm all pass**
```bash
make test-local
```

**Step 3: Commit**
```bash
git add bot/commands/schedule.py
git commit -m "Wire assign_home_away into /schedule create"
```

---

## Task 9: Full test run and merge

**Step 1: Run the full Docker test suite**
```bash
cp /usr/local/share/ca-certificates/proxy-ca.crt /Users/josh/Code/cfb-bot/proxy-ca.crt
make test PROXY=http://host.docker.internal:3128
# Expected: all tests pass
```

**Step 2: Update CHANGELOG.md**

Run `/update-changelog` or manually add to `## [Unreleased]`:

```markdown
### Added
- Home/away assignment for every scheduled non-conference game, optimized by CP-SAT to minimize per-team imbalance

### Changed
- `/conference_schedule` now requires a `home_games` integer argument (number of home conference games)
- `/schedule create` and `/schedule show` output now displays `{home} vs. {away}` or `{away} at {home}` notation
```

**Step 3: Commit changelog**
```bash
git add CHANGELOG.md
git commit -m "Update changelog for Feature 2"
```

**Step 4: Squash merge to main**
```bash
git checkout main
git merge --squash feature/homeaway-balancing
git commit -m "Release 0.5.0: home/away balancing for non-conference games"
git tag -a v0.5.0 -m "Release 0.5.0"
git branch -d feature/homeaway-balancing
```
