"""Tests for the CP-SAT scheduler."""

import pytest

from solver.model import Assignment, Request, SolverInput, SolverResult, Team
from solver.scheduler import solve


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def human(name: str, conf_weeks: list[int] = []) -> Team:
    return Team(name=name, conference_weeks=frozenset(conf_weeks), is_cpu=False)


def cpu(name: str) -> Team:
    return Team(name=name, conference_weeks=frozenset(), is_cpu=True)


def req(a: str, b: str) -> Request:
    return Request(team_a=a, team_b=b)


def fulfilled_pairs(result: SolverResult) -> set[tuple[str, str]]:
    return {(a.request.team_a, a.request.team_b) for a in result.assignments}


# ---------------------------------------------------------------------------
# Basic correctness
# ---------------------------------------------------------------------------

class TestBasicScheduling:
    def test_single_request_no_conflicts_is_scheduled(self):
        teams = {"Alabama": human("Alabama"), "Auburn": human("Auburn")}
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Auburn")]))
        assert len(result.assignments) == 1
        assert len(result.unscheduled) == 0
        assert result.assignments[0].week in range(1, 15)

    def test_empty_request_list_returns_empty_result(self):
        result = solve(SolverInput(teams={}, requests=[]))
        assert result.assignments == []
        assert result.unscheduled == []

    def test_multiple_requests_all_fulfilled_when_possible(self):
        # 4 independent teams, each with plenty of open weeks
        teams = {
            "Alabama": human("Alabama", [1, 2, 3, 4, 5, 6, 7, 8]),
            "Auburn": human("Auburn", [1, 2, 3, 4, 5, 6, 7, 8]),
            "Georgia": human("Georgia", [1, 2, 3, 4, 5, 6, 7, 8]),
            "LSU": human("LSU", [1, 2, 3, 4, 5, 6, 7, 8]),
        }
        requests = [req("Alabama", "Auburn"), req("Georgia", "LSU")]
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 2
        assert len(result.unscheduled) == 0

    def test_assigned_week_is_valid(self):
        teams = {"Alabama": human("Alabama"), "Auburn": human("Auburn")}
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Auburn")]))
        for a in result.assignments:
            assert 1 <= a.week <= 14


# ---------------------------------------------------------------------------
# Hard constraint: conference game conflict
# ---------------------------------------------------------------------------

class TestConferenceConflict:
    def test_request_not_assigned_to_conf_week_of_team_a(self):
        # Game must not land on Alabama's only conference week
        teams = {
            "Alabama": human("Alabama", [5]),  # nc_cap=11
            "Notre Dame": human("Notre Dame"),
        }
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Notre Dame")]))
        assert len(result.assignments) == 1
        assert result.assignments[0].week != 5

    def test_request_not_assigned_to_conf_week_of_team_b(self):
        # Same as above but team order in the request is reversed
        teams = {
            "Notre Dame": human("Notre Dame"),
            "Alabama": human("Alabama", [5]),
        }
        result = solve(SolverInput(teams=teams, requests=[req("Notre Dame", "Alabama")]))
        assert len(result.assignments) == 1
        assert result.assignments[0].week != 5

    def test_request_unscheduled_when_all_weeks_blocked(self):
        # Alabama covers weeks 1-7, Auburn covers weeks 8-14 — no shared open week
        teams = {
            "Alabama": human("Alabama", list(range(1, 8))),   # nc_cap=5
            "Auburn": human("Auburn", list(range(8, 15))),    # nc_cap=5
        }
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Auburn")]))
        assert len(result.assignments) == 0
        assert len(result.unscheduled) == 1

    def test_combined_conf_weeks_of_both_teams_are_blocked(self):
        # Alabama: conf weeks 1-7, Auburn: conf weeks 8-13 → only week 14 open
        teams = {
            "Alabama": human("Alabama", list(range(1, 8))),
            "Auburn": human("Auburn", list(range(8, 14))),
        }
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Auburn")]))
        assert len(result.assignments) == 1
        assert result.assignments[0].week == 14


# ---------------------------------------------------------------------------
# Hard constraint: no double-booking
# ---------------------------------------------------------------------------

class TestNoDoubleBooking:
    def test_nc_cap_limits_to_one_game_per_team(self):
        # Alabama has nc_cap=1 (11 conf games), two requests → only 1 fulfilled
        teams = {
            "Alabama": human("Alabama", list(range(1, 12))),  # nc_cap=1
            "Auburn": human("Auburn"),
            "Georgia": human("Georgia"),
        }
        requests = [req("Alabama", "Auburn"), req("Alabama", "Georgia")]
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 1
        assert len(result.unscheduled) == 1

    def test_two_requests_same_week_different_teams_both_scheduled(self):
        # Two independent matchups can share a week since they don't overlap
        teams = {
            "Alabama": human("Alabama", list(range(1, 9))),
            "Auburn": human("Auburn", list(range(1, 9))),
            "Georgia": human("Georgia", list(range(1, 9))),
            "LSU": human("LSU", list(range(1, 9))),
        }
        requests = [req("Alabama", "Auburn"), req("Georgia", "LSU")]
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 2
        weeks = [a.week for a in result.assignments]
        assert all(w in range(1, 15) for w in weeks)

    def test_maximize_fulfillment_when_team_appears_in_multiple_requests(self):
        # Alabama has nc_cap=2 (10 conf games), 3 requests → max 2 fulfilled
        teams = {
            "Alabama": human("Alabama", list(range(1, 11))),  # nc_cap=2
            "Auburn": human("Auburn"),
            "Georgia": human("Georgia"),
            "LSU": human("LSU"),
        }
        requests = [
            req("Alabama", "Auburn"),
            req("Alabama", "Georgia"),
            req("Alabama", "LSU"),
        ]
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 2
        assert len(result.unscheduled) == 1

    def test_cpu_team_not_double_booked_in_same_week(self):
        # Three human teams all want to play Army (CPU) in overlapping open weeks.
        # Army must be assigned to three different weeks.
        teams = {
            "TeamA": human("TeamA", list(range(1, 10))),  # open 10-14, nc_cap=3
            "TeamB": human("TeamB", list(range(1, 10))),
            "TeamC": human("TeamC", list(range(1, 10))),
        }
        requests = [req("TeamA", "Army"), req("TeamB", "Army"), req("TeamC", "Army")]
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 3
        army_weeks = [a.week for a in result.assignments]
        assert len(army_weeks) == len(set(army_weeks))  # no duplicate weeks for Army


# ---------------------------------------------------------------------------
# Hard constraint: NC cap
# ---------------------------------------------------------------------------

class TestNcCap:
    def test_team_not_assigned_more_than_nc_cap(self):
        # Alabama: 9 conf games → nc_cap=3. Four requests → max 3 fulfilled.
        teams = {
            "Alabama": human("Alabama", [1, 2, 3, 4, 5, 6, 7, 8, 9]),
            "Auburn": human("Auburn"),
            "Georgia": human("Georgia"),
            "LSU": human("LSU"),
            "Notre Dame": human("Notre Dame"),
        }
        requests = [
            req("Alabama", "Auburn"),
            req("Alabama", "Georgia"),
            req("Alabama", "LSU"),
            req("Alabama", "Notre Dame"),
        ]
        result = solve(SolverInput(teams=teams, requests=requests))
        alabama_games = sum(
            1 for a in result.assignments
            if a.request.team_a == "Alabama" or a.request.team_b == "Alabama"
        )
        assert alabama_games <= 3

    def test_nc_cap_zero_blocks_all_nc_games(self):
        # Team with 12 conf games has nc_cap=0 — no NC games possible
        teams = {
            "Alabama": human("Alabama", list(range(1, 13))),  # nc_cap=0
            "Auburn": human("Auburn"),
        }
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Auburn")]))
        assert len(result.assignments) == 0
        assert len(result.unscheduled) == 1

    def test_cpu_team_has_no_cap(self):
        # 13 human teams (each with 1 conf game, nc_cap=11) all want to play Army (CPU).
        # Army ends up playing 13 games — more than the 12 that would cap a human team.
        teams = {}
        requests = []
        for i in range(13):
            name = f"Team{i}"
            teams[name] = human(name, [i + 1])  # each team blocked on a different week
            requests.append(req(name, "Army"))
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 13  # Army plays 13 games — no cap enforced


# ---------------------------------------------------------------------------
# Optimization: maximize fulfilled requests
# ---------------------------------------------------------------------------

class TestOptimization:
    def test_solver_maximizes_fulfilled_requests(self):
        # Alabama has nc_cap=1 (11 conf games).
        # Alabama-Auburn and Alabama-Georgia both compete for Alabama's 1 NC slot.
        # LSU-Georgia is independent and always schedulable.
        # Optimal: 2 games (1 Alabama game + LSU vs Georgia).
        teams = {
            "Alabama": human("Alabama", list(range(1, 12))),  # nc_cap=1
            "Auburn": human("Auburn"),
            "Georgia": human("Georgia"),
            "LSU": human("LSU"),
        }
        requests = [
            req("Alabama", "Auburn"),
            req("Alabama", "Georgia"),
            req("LSU", "Georgia"),
        ]
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 2

    def test_all_requests_unscheduled_when_no_valid_week_exists(self):
        # Combined conf schedules cover all 14 weeks — no open slot
        teams = {
            "Alabama": human("Alabama", list(range(1, 8))),
            "Auburn": human("Auburn", list(range(8, 15))),
        }
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Auburn")]))
        assert result.assignments == []
        assert len(result.unscheduled) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_only_one_valid_week_is_used(self):
        # Alabama: conf weeks 1-7, Auburn: conf weeks 8-13 → only week 14 open
        teams = {
            "Alabama": human("Alabama", list(range(1, 8))),   # nc_cap=5
            "Auburn": human("Auburn", list(range(8, 14))),    # nc_cap=6
        }
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Auburn")]))
        assert len(result.assignments) == 1
        assert result.assignments[0].week == 14

    def test_cpu_team_implicit_from_request(self):
        # CPU team not in teams dict — auto-registered and schedulable
        teams = {"Alabama": human("Alabama")}
        result = solve(SolverInput(teams=teams, requests=[req("Alabama", "Army")]))
        assert len(result.assignments) == 1

    def test_team_in_multiple_requests_each_different_opponent(self):
        # Alabama: 9 conf games (nc_cap=3), open weeks 10-14. Three requests.
        # All three can be scheduled since nc_cap allows it and weeks are available.
        teams = {
            "Alabama": human("Alabama", list(range(1, 10))),  # nc_cap=3, open 10-14
            "Auburn": human("Auburn"),
            "Georgia": human("Georgia"),
            "LSU": human("LSU"),
        }
        requests = [
            req("Alabama", "Auburn"),
            req("Alabama", "Georgia"),
            req("Alabama", "LSU"),
        ]
        result = solve(SolverInput(teams=teams, requests=requests))
        assert len(result.assignments) == 3
        weeks = [a.week for a in result.assignments]
        assert len(set(weeks)) == 3  # each assigned a different week

    def test_no_duplicate_week_assignments_for_same_team(self):
        teams = {
            "Alabama": human("Alabama"),
            "Auburn": human("Auburn"),
            "Georgia": human("Georgia"),
        }
        requests = [req("Alabama", "Auburn"), req("Alabama", "Georgia")]
        result = solve(SolverInput(teams=teams, requests=requests))
        alabama_weeks = [
            a.week for a in result.assignments
            if a.request.team_a == "Alabama" or a.request.team_b == "Alabama"
        ]
        assert len(alabama_weeks) == len(set(alabama_weeks))

    def test_result_weeks_are_within_valid_range(self):
        teams = {f"Team{i}": human(f"Team{i}") for i in range(6)}
        requests = [req(f"Team{i*2}", f"Team{i*2+1}") for i in range(3)]
        result = solve(SolverInput(teams=teams, requests=requests))
        for a in result.assignments:
            assert 1 <= a.week <= 14

    def test_all_requests_return_in_assignments_or_unscheduled(self):
        teams = {
            "Alabama": human("Alabama"),
            "Auburn": human("Auburn"),
            "Georgia": human("Georgia"),
            "LSU": human("LSU"),
        }
        requests = [req("Alabama", "Auburn"), req("Georgia", "LSU")]
        result = solve(SolverInput(teams=teams, requests=requests))
        total = len(result.assignments) + len(result.unscheduled)
        assert total == len(requests)
