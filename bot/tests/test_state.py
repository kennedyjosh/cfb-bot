"""Tests for bot/state.py — GuildState."""

import pytest

from bot.state import GuildState
from solver.model import Request


class TestSetConferenceSchedule:
    def test_new_entry_returns_false(self):
        state = GuildState()
        assert state.set_conference_schedule("Alabama", [1, 3, 5]) is False

    def test_updated_entry_returns_true(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5])
        assert state.set_conference_schedule("Alabama", [2, 4, 6]) is True

    def test_weeks_stored_correctly(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5])
        assert state.conference_schedules["Alabama"] == {1, 3, 5}

    def test_replaces_prior_entry(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5])
        state.set_conference_schedule("Alabama", [2, 4, 6])
        assert state.conference_schedules["Alabama"] == {2, 4, 6}

    def test_multiple_teams_stored_independently(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3])
        state.set_conference_schedule("Auburn", [5, 7])
        assert state.conference_schedules["Alabama"] == {1, 3}
        assert state.conference_schedules["Auburn"] == {5, 7}


class TestAddRequest:
    def test_request_appended(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        assert len(state.requests) == 1
        assert state.requests[0].team_a == "Alabama"
        assert state.requests[0].team_b == "Auburn"

    def test_returns_request_object(self):
        state = GuildState()
        req = state.add_request("Georgia", "LSU")
        assert isinstance(req, Request)
        assert req.team_a == "Georgia"
        assert req.team_b == "LSU"

    def test_multiple_requests_preserved_in_order(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        state.add_request("Georgia", "LSU")
        assert state.requests[0].team_a == "Alabama"
        assert state.requests[1].team_a == "Georgia"


class TestHasDuplicateRequest:
    def test_no_duplicate_when_empty(self):
        state = GuildState()
        assert state.has_duplicate_request("Alabama", "Auburn") is False

    def test_detects_exact_duplicate(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        assert state.has_duplicate_request("Alabama", "Auburn") is True

    def test_detects_reversed_duplicate(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        assert state.has_duplicate_request("Auburn", "Alabama") is True

    def test_different_pair_not_duplicate(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        assert state.has_duplicate_request("Alabama", "Georgia") is False


class TestTeamsMissingConfSchedule:
    def test_no_requests_returns_empty(self):
        state = GuildState()
        assert state.teams_missing_conf_schedule({"Alabama"}) == []

    def test_all_schedules_present_returns_empty(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        state.set_conference_schedule("Alabama", [1])
        state.set_conference_schedule("Auburn", [2])
        assert state.teams_missing_conf_schedule({"Alabama", "Auburn"}) == []

    def test_missing_team_returned(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        state.set_conference_schedule("Auburn", [2])
        missing = state.teams_missing_conf_schedule({"Alabama", "Auburn"})
        assert missing == ["Alabama"]

    def test_cpu_teams_not_returned(self):
        # Army is not in human_teams, so it should be treated as CPU and excluded
        state = GuildState()
        state.add_request("Alabama", "Army")
        state.set_conference_schedule("Alabama", [1])
        missing = state.teams_missing_conf_schedule({"Alabama"})
        assert missing == []

    def test_returns_sorted_list(self):
        state = GuildState()
        state.add_request("Georgia", "Notre Dame")
        state.add_request("Alabama", "Auburn")
        missing = state.teams_missing_conf_schedule(
            {"Alabama", "Auburn", "Georgia", "Notre Dame"}
        )
        assert missing == sorted(missing)
