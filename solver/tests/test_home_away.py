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
