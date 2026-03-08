"""Tests for bot/state.py — GuildState."""

import pytest

from bot.state import GuildState
from solver.model import Request, SolverResult


class TestSetConferenceSchedule:
    def test_new_entry_returns_false(self):
        state = GuildState()
        assert state.set_conference_schedule("Alabama", [1, 3, 5], home_games=0) is False

    def test_updated_entry_returns_true(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5], home_games=0)
        assert state.set_conference_schedule("Alabama", [2, 4, 6], home_games=0) is True

    def test_weeks_stored_correctly(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5], home_games=0)
        assert state.conference_schedules["Alabama"] == {1, 3, 5}

    def test_replaces_prior_entry(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3, 5], home_games=0)
        state.set_conference_schedule("Alabama", [2, 4, 6], home_games=0)
        assert state.conference_schedules["Alabama"] == {2, 4, 6}

    def test_multiple_teams_stored_independently(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=0)
        state.set_conference_schedule("Auburn", [5, 7], home_games=0)
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
        state.set_conference_schedule("Alabama", [1], home_games=0)
        state.set_conference_schedule("Auburn", [2], home_games=0)
        assert state.teams_missing_conf_schedule({"Alabama", "Auburn"}) == []

    def test_missing_team_returned(self):
        state = GuildState()
        state.add_request("Alabama", "Auburn")
        state.set_conference_schedule("Auburn", [2], home_games=0)
        missing = state.teams_missing_conf_schedule({"Alabama", "Auburn"})
        assert missing == ["Alabama"]

    def test_cpu_teams_not_returned(self):
        # Army is not in human_teams, so it should be treated as CPU and excluded
        state = GuildState()
        state.add_request("Alabama", "Army")
        state.set_conference_schedule("Alabama", [1], home_games=0)
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

    def test_same_name_rename_nulls_last_result_and_preserves_schedule(self):
        state = GuildState()
        state.set_conference_schedule("Alabama", [1, 3], home_games=2)
        state.add_request("Alabama", "Notre Dame")
        state.last_result = _mock_result()
        summary = state.rename_team("Alabama", "Alabama")
        assert summary == {"removed": 0, "readded": 0, "skipped": 0}
        assert "Alabama" in state.conference_schedules
        assert "Alabama" in state.conference_home_games
        assert len(state.requests) == 1
        assert state.last_result is None
