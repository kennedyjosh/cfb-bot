"""Tests for bot/formatting.py — pure functions, no Discord dependency."""

import pytest

from bot.formatting import (
    ADMIN_WARNING,
    fmt_conf_schedule_set,
    fmt_request_added,
    fmt_schedule_result,
    fmt_schedule_show,
    fmt_teams,
)
from solver.model import Assignment, Request, SolverResult


# ---------------------------------------------------------------------------
# fmt_conf_schedule_set
# ---------------------------------------------------------------------------


class TestFmtConfScheduleSet:
    def test_new_entry(self):
        result = fmt_conf_schedule_set("Alabama", [1, 3, 5], updated=False)
        assert result.startswith("Set conference schedule for Alabama.")
        assert "weeks 1 3 5" in result

    def test_updated_entry(self):
        result = fmt_conf_schedule_set("Auburn", [2, 4], updated=True)
        assert result.startswith("Updated conference schedule for Auburn.")
        assert "weeks 2 4" in result

    def test_weeks_are_sorted(self):
        result = fmt_conf_schedule_set("Georgia", [9, 3, 1], updated=False)
        assert "weeks 1 3 9" in result

    def test_single_week(self):
        result = fmt_conf_schedule_set("Army", [7], updated=False)
        assert "weeks 7" in result

    def test_team_name_appears_in_both_lines(self):
        result = fmt_conf_schedule_set("Notre Dame", [1, 2, 3], updated=False)
        assert result.count("Notre Dame") == 2


# ---------------------------------------------------------------------------
# fmt_request_added
# ---------------------------------------------------------------------------


class TestFmtRequestAdded:
    def test_basic(self):
        result = fmt_request_added("Alabama", "Auburn", index=1, total=1)
        assert "Alabama vs. Auburn" in result
        assert "Request #1 of 1" in result

    def test_index_and_total_appear(self):
        result = fmt_request_added("Georgia", "LSU", index=3, total=5)
        assert "Request #3 of 5" in result

    def test_team_names_appear(self):
        result = fmt_request_added("Notre Dame", "Army", index=2, total=4)
        assert "Notre Dame vs. Army" in result


# ---------------------------------------------------------------------------
# fmt_schedule_result
# ---------------------------------------------------------------------------


def _req(a: str, b: str) -> Request:
    return Request(team_a=a, team_b=b)


def _assignment(a: str, b: str, week: int) -> Assignment:
    return Assignment(request=_req(a, b), week=week)


class TestFmtScheduleResult:
    def test_header_shows_counts(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[],
        )
        text = fmt_schedule_result(result)
        assert "1 of 1 requests fulfilled" in text

    def test_fulfilled_game_listed(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[],
        )
        text = fmt_schedule_result(result)
        assert "Week 3: Alabama vs. Auburn" in text

    def test_no_unscheduled_section_when_all_fulfilled(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[],
        )
        text = fmt_schedule_result(result)
        assert "Not scheduled" not in text

    def test_unscheduled_section_appears(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result)
        assert "Not scheduled:" in text
        assert "Alabama vs. Auburn" in text

    def test_none_fulfilled_shows_none_placeholder(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result)
        assert "(none)" in text

    def test_fulfilled_sorted_by_week(self):
        result = SolverResult(
            assignments=[
                _assignment("Georgia", "LSU", 9),
                _assignment("Alabama", "Auburn", 3),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result)
        week3_pos = text.index("Week 3")
        week9_pos = text.index("Week 9")
        assert week3_pos < week9_pos

    def test_fulfilled_sorted_alphabetically_within_week(self):
        result = SolverResult(
            assignments=[
                _assignment("Notre Dame", "Army", 5),
                _assignment("Alabama", "Auburn", 5),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result)
        alabama_pos = text.index("Alabama")
        notre_dame_pos = text.index("Notre Dame")
        assert alabama_pos < notre_dame_pos

    def test_counts_reflect_total_requests(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[_req("Georgia", "LSU")],
        )
        text = fmt_schedule_result(result)
        assert "1 of 2 requests fulfilled" in text

    def test_all_unscheduled(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn"), _req("Georgia", "LSU")],
        )
        text = fmt_schedule_result(result)
        assert "0 of 2 requests fulfilled" in text


# ---------------------------------------------------------------------------
# fmt_schedule_show
# ---------------------------------------------------------------------------


class TestFmtScheduleShow:
    def test_no_games(self):
        text = fmt_schedule_show("Alabama", [])
        assert "Alabama has no non-conference games scheduled." == text

    def test_single_game_as_team_a(self):
        a = _assignment("Alabama", "Auburn", 5)
        text = fmt_schedule_show("Alabama", [a])
        assert "Non-conference schedule for Alabama:" in text
        assert "Week 5: Alabama vs. Auburn" in text

    def test_single_game_as_team_b(self):
        # Opponent is team_a — should still show correctly
        a = _assignment("Auburn", "Alabama", 5)
        text = fmt_schedule_show("Alabama", [a])
        assert "Week 5: Alabama vs. Auburn" in text

    def test_multiple_games_sorted_by_week(self):
        assignments = [
            _assignment("Alabama", "Georgia", 9),
            _assignment("Alabama", "Auburn", 3),
        ]
        text = fmt_schedule_show("Alabama", assignments)
        week3_pos = text.index("Week 3")
        week9_pos = text.index("Week 9")
        assert week3_pos < week9_pos

    def test_opponent_name_appears(self):
        a = _assignment("Alabama", "Notre Dame", 7)
        text = fmt_schedule_show("Alabama", [a])
        assert "Notre Dame" in text


# ---------------------------------------------------------------------------
# fmt_teams
# ---------------------------------------------------------------------------


class TestFmtTeams:
    def test_all_mapped(self):
        text = fmt_teams(ignored=[], unparsable=[])
        assert text == "All members have been successfully mapped to a team."

    def test_ignored_only(self):
        text = fmt_teams(ignored=["Josh (Inactive)"], unparsable=[])
        assert "Ignored (matched ignore_regex):" in text
        assert "Josh (Inactive)" in text
        assert "Unparsable" not in text

    def test_unparsable_only(self):
        text = fmt_teams(ignored=[], unparsable=["RandomGuy"])
        assert "Unparsable (name not recognized):" in text
        assert "RandomGuy" in text
        assert "Ignored" not in text

    def test_both_sections(self):
        text = fmt_teams(ignored=["Inactive1"], unparsable=["Typo Team"])
        assert "Ignored (matched ignore_regex):" in text
        assert "Inactive1" in text
        assert "Unparsable (name not recognized):" in text
        assert "Typo Team" in text

    def test_header_present_when_any_unresolved(self):
        text = fmt_teams(ignored=["X"], unparsable=[])
        assert "Members not mapped to a team:" in text

    def test_multiple_names_per_section(self):
        text = fmt_teams(ignored=["A", "B"], unparsable=["C", "D"])
        assert "A" in text
        assert "B" in text
        assert "C" in text
        assert "D" in text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_admin_warning_mentions_config(self):
        assert "admin.id" in ADMIN_WARNING
        assert "config/" in ADMIN_WARNING
