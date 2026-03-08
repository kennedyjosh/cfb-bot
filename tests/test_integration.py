"""
Integration tests: GuildState → solver → formatters (no Discord mocking).

These tests exercise the full application data flow across layers:
  1. Populate GuildState with conference schedules and requests
  2. Build solver input as schedule_create does
  3. Run solve() and assign_home_away()
  4. Pass the result to fmt_schedule_result / fmt_schedule_show
  5. Assert on the combined output

This catches bugs at the seams: wrong field extraction from state,
mismatched data structures between layers, and incorrect end-to-end
behavior on realistic multi-team scenarios.
"""

from bot.formatting import fmt_schedule_result, fmt_schedule_show
from bot.state import GuildState
from solver.model import SolverInput, SolverResult, Team
from solver.scheduler import assign_home_away, solve


def _build_teams(state: GuildState) -> dict[str, Team]:
    """Build the Team dict from GuildState, mirroring schedule_create."""
    return {
        name: Team(
            name=name,
            conference_weeks=frozenset(weeks),
            is_cpu=False,
            conference_home_games=state.conference_home_games.get(name, 0),
        )
        for name, weeks in state.conference_schedules.items()
    }


def _run_solver(state: GuildState) -> tuple[SolverResult, dict[str, Team]]:
    """Run the full solve + assign_home_away pipeline from state."""
    teams = _build_teams(state)
    raw = solve(SolverInput(teams=teams, requests=state.requests))
    result = SolverResult(
        assignments=assign_home_away(raw.assignments, teams),
        unscheduled=raw.unscheduled,
    )
    state.last_result = result
    return result, teams


# ---------------------------------------------------------------------------
# schedule create workflow
# ---------------------------------------------------------------------------


class TestScheduleCreateWorkflow:
    """GuildState → solve() → assign_home_away() → fmt_schedule_result()."""

    def test_all_requests_fulfilled(self, dynasty_state):
        result, teams = _run_solver(dynasty_state)
        output = fmt_schedule_result(result, teams)

        assert len(result.unscheduled) == 0
        assert "4 of 4 requests fulfilled" in output

    def test_output_contains_all_human_team_sections(self, dynasty_state):
        result, teams = _run_solver(dynasty_state)
        output = fmt_schedule_result(result, teams)

        # Each human team appears in the per-team schedule section
        assert "Alabama" in output
        assert "Auburn" in output
        assert "Georgia" in output

    def test_game_lines_include_home_away_notation(self, dynasty_state):
        result, teams = _run_solver(dynasty_state)
        output = fmt_schedule_result(result, teams)

        game_lines = [l for l in output.splitlines() if l.strip().startswith("Week")]
        assert len(game_lines) > 0
        assert all("vs." in l or " at " in l for l in game_lines)


# ---------------------------------------------------------------------------
# schedule show workflow
# ---------------------------------------------------------------------------


class TestScheduleShowWorkflow:
    """GuildState + solver result → fmt_schedule_show()."""

    def _show(self, state: GuildState, team: str) -> str:
        """Extract data from state and format schedule show, as schedule_show does."""
        conf_weeks = state.conference_schedules.get(team)
        conf_home = state.conference_home_games.get(team, 0)
        if state.last_result is None:
            assignments = None
        else:
            assignments = [
                a for a in state.last_result.assignments
                if a.request.team_a == team or a.request.team_b == team
            ]
        return fmt_schedule_show(team, conf_weeks, assignments, conference_home_games=conf_home)

    def test_conference_schedule_shown_before_solve(self, dynasty_state):
        # state.last_result is None — conference schedule should still appear
        output = self._show(dynasty_state, "Alabama")

        assert "Conference (6 games)" in output
        assert "not yet scheduled" in output

    def test_nc_games_and_conference_shown_after_solve(self, dynasty_state):
        _run_solver(dynasty_state)
        output = self._show(dynasty_state, "Alabama")

        # Alabama is in 3 requests: vs. Auburn, vs. Georgia, vs. Purdue
        assert "Conference (6 games)" in output
        assert "Non-conference (3 games)" in output

    def test_bye_weeks_shown_after_solve(self, dynasty_state):
        _run_solver(dynasty_state)
        output = self._show(dynasty_state, "Alabama")

        # Alabama: 6 conf + 3 NC = 9 games total, so 5 bye weeks (out of 14)
        assert "Bye weeks:" in output

    def test_cpu_advice_reflects_open_nc_slots(self, dynasty_state):
        _run_solver(dynasty_state)
        output = self._show(dynasty_state, "Alabama")

        # Alabama nc_cap=6, 3 NC games scheduled → 3 open slots remaining
        assert "Open slots: 3" in output

    def test_cpu_advice_absent_when_schedule_full(self):
        # A team with nc_cap=2 that fills both slots has no open slots
        state = GuildState()
        state.set_conference_schedule("Alabama", list(range(1, 11)), 5)  # nc_cap=2
        state.set_conference_schedule("Auburn",  list(range(1, 11)), 5)  # nc_cap=2
        state.add_request("Alabama", "Auburn")
        state.add_request("Alabama", "LSU")  # LSU = CPU

        result, teams = _run_solver(state)
        conf_weeks = state.conference_schedules.get("Alabama")
        conf_home = state.conference_home_games.get("Alabama", 0)
        assignments = [
            a for a in result.assignments
            if a.request.team_a == "Alabama" or a.request.team_b == "Alabama"
        ]
        output = fmt_schedule_show("Alabama", conf_weeks, assignments, conference_home_games=conf_home)

        assert "Open slots" not in output


# ---------------------------------------------------------------------------
# Unscheduled reason propagation
# ---------------------------------------------------------------------------


class TestUnscheduledReasonPropagation:
    """Unschedulable requests → correct reason text in fmt_schedule_result."""

    def test_cap_zero_team_shows_schedule_full_reason(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5, 7, 9, 11], 3)  # nc_cap=6
        state.set_conference_schedule("LSU", list(range(1, 13)), 6)         # nc_cap=0

        state.add_request("Alabama", "LSU")

        result, teams = _run_solver(state)
        output = fmt_schedule_result(result, teams)

        assert "0 of 1 requests fulfilled" in output
        assert "Alabama vs. LSU" in output
        assert "LSU's schedule is full" in output

    def test_no_common_open_week_reason(self):
        # Two teams whose conference weeks together block all 14 weeks
        # Alabama: 1-7 (7 games), Auburn: 8-14 (7 games) → no open week together
        state = GuildState()
        state.set_conference_schedule("Alabama", list(range(1, 8)), 4)   # weeks 1-7
        state.set_conference_schedule("Auburn",  list(range(8, 15)), 3)  # weeks 8-14

        state.add_request("Alabama", "Auburn")

        result, teams = _run_solver(state)
        output = fmt_schedule_result(result, teams)

        assert "0 of 1 requests fulfilled" in output
        assert "no common open week" in output
