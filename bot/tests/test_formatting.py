"""Tests for bot/formatting.py — pure functions, no Discord dependency."""

import pytest

from bot.formatting import (
    ADMIN_WARNING,
    fmt_conf_schedule_set,
    fmt_cpu_team_rejected,
    fmt_request_added,
    fmt_request_removed,
    fmt_schedule_result,
    fmt_schedule_show,
    fmt_teams,
)
from solver.model import Assignment, Request, SolverResult, Team


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _req(a: str, b: str) -> Request:
    return Request(team_a=a, team_b=b)


def _assignment(a: str, b: str, week: int, home_team: str = "") -> Assignment:
    return Assignment(request=_req(a, b), week=week, home_team=home_team)


def _human(name: str, conf_weeks: list[int] = [], conf_home: int = 0) -> Team:
    return Team(name=name, conference_weeks=frozenset(conf_weeks), is_cpu=False, conference_home_games=conf_home)


# ---------------------------------------------------------------------------
# fmt_cpu_team_rejected
# ---------------------------------------------------------------------------


class TestFmtCpuTeamRejected:
    def test_contains_team_name(self):
        text = fmt_cpu_team_rejected("Army")
        assert "Army" in text

    def test_indicates_cpu_team(self):
        text = fmt_cpu_team_rejected("Army")
        assert "CPU" in text


# ---------------------------------------------------------------------------
# fmt_conf_schedule_set
# ---------------------------------------------------------------------------


class TestFmtConfScheduleSet:
    def test_new_entry(self):
        result = fmt_conf_schedule_set("Alabama", [1, 3, 5], home_games=0, updated=False)
        assert result.startswith("Set conference schedule for Alabama.")
        assert "weeks 1 3 5" in result

    def test_updated_entry(self):
        result = fmt_conf_schedule_set("Auburn", [2, 4], home_games=0, updated=True)
        assert result.startswith("Updated conference schedule for Auburn.")
        assert "weeks 2 4" in result

    def test_weeks_are_sorted(self):
        result = fmt_conf_schedule_set("Georgia", [9, 3, 1], home_games=0, updated=False)
        assert "weeks 1 3 9" in result


class TestFmtConfScheduleSetHomeGames:
    def test_home_games_shown_in_confirmation(self):
        result = fmt_conf_schedule_set("Alabama", [1, 3, 5], home_games=3, updated=False)
        assert "3 home" in result

    def test_single_week(self):
        result = fmt_conf_schedule_set("Army", [7], home_games=0, updated=False)
        assert "weeks 7" in result

    def test_team_name_appears_in_both_lines(self):
        result = fmt_conf_schedule_set("Notre Dame", [1, 2, 3], home_games=0, updated=False)
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
# fmt_request_removed
# ---------------------------------------------------------------------------


class TestFmtRequestRemoved:
    def test_contains_both_team_names(self):
        result = fmt_request_removed("Alabama", "Auburn")
        assert "Alabama vs. Auburn" in result

    def test_indicates_removal(self):
        result = fmt_request_removed("Alabama", "Auburn")
        assert "Request removed:" in result


# ---------------------------------------------------------------------------
# fmt_schedule_result — header
# ---------------------------------------------------------------------------


class TestFmtScheduleResultHeader:
    def test_counts_all_fulfilled(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        assert "1 of 1 requests fulfilled" in text

    def test_counts_partial(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[_req("Georgia", "LSU")],
        )
        text = fmt_schedule_result(result, {})
        assert "1 of 2 requests fulfilled" in text

    def test_counts_none_fulfilled(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn"), _req("Georgia", "LSU")],
        )
        text = fmt_schedule_result(result, {})
        assert "0 of 2 requests fulfilled" in text


# ---------------------------------------------------------------------------
# fmt_schedule_result — not-scheduled section
# ---------------------------------------------------------------------------


class TestFmtScheduleResultUnscheduled:
    def test_no_unscheduled_section_when_all_fulfilled(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        assert "Not scheduled" not in text

    def test_unscheduled_section_appears(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, {})
        assert "Not scheduled" in text
        assert "Alabama vs. Auburn" in text

    def test_unscheduled_section_before_schedule(self):
        # Unscheduled section must appear before the per-team schedule.
        result = SolverResult(
            assignments=[_assignment("Georgia", "LSU", 5)],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, {})
        assert text.index("Not scheduled") < text.index("Georgia")

    def test_unscheduled_header_shows_count(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, {})
        assert "Not scheduled (1):" in text

    def test_multiple_unscheduled_shown(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn"), _req("Georgia", "LSU")],
        )
        text = fmt_schedule_result(result, {})
        assert "Not scheduled (2):" in text
        assert "Alabama vs. Auburn" in text
        assert "Georgia vs. LSU" in text

    def test_reason_no_common_open_week(self):
        # Alabama: weeks 1-7, Auburn: weeks 8-14 — every week is blocked for one of them.
        teams = {
            "Alabama": _human("Alabama", list(range(1, 8))),
            "Auburn": _human("Auburn", list(range(8, 15))),
        }
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, teams)
        assert "no common open week" in text

    def test_reason_nc_cap_full(self):
        # Alabama nc_cap=1, already has 1 game assigned → Alabama vs Auburn unscheduled.
        teams = {
            "Alabama": _human("Alabama", list(range(1, 12))),  # nc_cap=1
            "Auburn": _human("Auburn"),
            "Georgia": _human("Georgia"),
        }
        result = SolverResult(
            assignments=[_assignment("Alabama", "Georgia", 12)],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, teams)
        assert "Alabama's schedule is full" in text

    def test_reason_scheduling_conflict_fallback(self):
        # Both teams have open weeks and nc_cap available — solver just couldn't fit it.
        teams = {
            "Alabama": _human("Alabama"),
            "Auburn": _human("Auburn"),
        }
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, teams)
        assert "scheduling conflict" in text


# ---------------------------------------------------------------------------
# fmt_schedule_result — home/away imbalance section
# ---------------------------------------------------------------------------


class TestFmtScheduleResultImbalance:
    def test_imbalance_section_absent_when_balanced(self):
        # Alabama: 4 conf (2H 2A) + 2 NC (1H 1A) = 3H 3A → balanced
        teams = {"Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=2)}
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Auburn", 5, home_team="Alabama"),
                _assignment("Alabama", "Georgia", 6, home_team="Georgia"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        assert "imbalance" not in text.lower()

    def test_imbalance_section_absent_when_diff_is_one(self):
        # Teams always play 12 games (even), so diff=1 is impossible in practice.
        # This test confirms the threshold is strictly >= 2.
        # Alabama: 4 conf (2H 2A) + 1 NC (1H 0A) = 3H 2A → diff=1, below threshold
        teams = {"Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=2)}
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 5, home_team="Alabama")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        assert "imbalance" not in text.lower()

    def test_imbalance_shown_for_home_heavy_team(self):
        # Alabama: 4 conf (4H 0A) + 2 NC (2H 0A) = 6H 0A → +6 home
        teams = {"Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=4)}
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Auburn", 5, home_team="Alabama"),
                _assignment("Alabama", "Georgia", 6, home_team="Alabama"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        assert "imbalance" in text.lower()
        assert "Alabama" in text
        assert "home" in text

    def test_imbalance_format_string(self):
        # Alabama: 4 conf (4H 0A) + 4 NC (4H 0A) = 8H 0A → 8H 0A (+8 home)
        teams = {"Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=4)}
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Auburn", 5, home_team="Alabama"),
                _assignment("Alabama", "Georgia", 6, home_team="Alabama"),
                _assignment("Alabama", "LSU", 7, home_team="Alabama"),
                _assignment("Alabama", "Ole Miss", 8, home_team="Alabama"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        assert "8H 0A (+8 home)" in text

    def test_imbalance_shown_for_away_heavy_team(self):
        # Alabama: 4 conf (0H 4A) + 2 NC (0H 2A) = 0H 6A → +6 away
        teams = {"Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=0)}
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Auburn", 5, home_team="Auburn"),
                _assignment("Alabama", "Georgia", 6, home_team="Georgia"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        assert "imbalance" in text.lower()
        assert "Alabama" in text
        assert "away" in text

    def test_multiple_teams_with_imbalance(self):
        # Both Alabama and Auburn are home-heavy.
        teams = {
            "Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=4),
            "Auburn": _human("Auburn", [1, 2, 3, 4], conf_home=4),
        }
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "LSU", 5, home_team="Alabama"),
                _assignment("Alabama", "Ole Miss", 6, home_team="Alabama"),
                _assignment("Auburn", "LSU", 7, home_team="Auburn"),
                _assignment("Auburn", "Ole Miss", 8, home_team="Auburn"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        imbalance_start = text.lower().index("imbalance")
        schedule_start = text.index("Non-conference schedule")
        imbalance_section = text[imbalance_start:schedule_start]
        assert "Alabama" in imbalance_section
        assert "Auburn" in imbalance_section

    def test_imbalance_section_before_schedule(self):
        # Imbalance section must appear before per-team schedule.
        teams = {"Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=4)}
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Auburn", 5, home_team="Alabama"),
                _assignment("Alabama", "Georgia", 6, home_team="Alabama"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        assert text.index("imbalance") < text.index("Auburn")

    def test_cpu_teams_excluded_from_imbalance(self):
        # Army is CPU — should not appear in imbalance section even if heavily home.
        teams = {"Alabama": _human("Alabama", [1, 2, 3, 4], conf_home=2)}
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Army", 5, home_team="Alabama"),
                _assignment("Alabama", "Army", 6, home_team="Alabama"),  # hypothetical
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, teams)
        # Army not in teams → not considered for imbalance
        # Alabama: 4 conf (2H 2A) + 2 NC (2H 0A) = 4H 2A → diff=2, shown
        # Just verify Army does not appear in the imbalance section (it appears in schedule)
        if "imbalance" in text.lower():
            imbalance_start = text.lower().index("imbalance")
            schedule_start = text.index("Non-conference schedule")
            imbalance_text = text[imbalance_start:schedule_start]
            assert "Army" not in imbalance_text


# ---------------------------------------------------------------------------
# fmt_schedule_result — per-team schedule
# ---------------------------------------------------------------------------


class TestFmtScheduleResultByTeam:
    def test_game_appears_under_both_teams(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3, home_team="Alabama")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        # Alabama section: home → "vs. Auburn"
        assert "vs. Auburn" in text
        # Auburn section: away → "at Alabama"
        assert "at Alabama" in text

    def test_teams_listed_alphabetically(self):
        result = SolverResult(
            assignments=[_assignment("Georgia", "Alabama", 5, home_team="Georgia")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        # Alabama comes before Georgia alphabetically
        assert text.index("Alabama") < text.index("Georgia")

    def test_games_within_team_sorted_by_week(self):
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Auburn", 9, home_team="Alabama"),
                _assignment("Alabama", "Georgia", 3, home_team="Alabama"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        # Within Alabama's section, week 3 must appear before week 9
        alabama_section_start = text.index("Alabama")
        auburn_section_start = text.index("Auburn")
        alabama_section = text[alabama_section_start:auburn_section_start]
        assert alabama_section.index("Week 3") < alabama_section.index("Week 9")

    def test_no_schedule_section_when_nothing_fulfilled(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, {})
        assert "Non-conference schedule" not in text

    def test_home_team_shows_vs(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3, home_team="Alabama")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        # Under Alabama: home → vs.
        alabama_pos = text.index("Alabama")
        auburn_pos = text.rindex("Auburn")  # last occurrence is in Auburn's section header
        alabama_section = text[alabama_pos:auburn_pos]
        assert "vs. Auburn" in alabama_section

    def test_away_team_shows_at(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3, home_team="Auburn")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        # Under Alabama: away → at Auburn
        assert "at Auburn" in text

    def test_cpu_team_appears_in_schedule(self):
        # CPU teams not in `teams` dict but should still show up in per-team listing
        result = SolverResult(
            assignments=[_assignment("Alabama", "Army", 5, home_team="Alabama")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {"Alabama": _human("Alabama")})
        assert "Army" in text

    def test_singular_game_label(self):
        # "1 game" (not "1 games") when a team has exactly one NC game
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3, home_team="Alabama")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        assert "Alabama (1 game):" in text

    def test_plural_games_label(self):
        result = SolverResult(
            assignments=[
                _assignment("Alabama", "Auburn", 3, home_team="Alabama"),
                _assignment("Alabama", "Georgia", 5, home_team="Alabama"),
            ],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        assert "Alabama (2 games):" in text

    def test_unset_home_team_shows_vs_for_both_teams(self):
        # home_team="" (unset) → both teams show "vs. opponent" (neutral display)
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3, home_team="")],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        # Both Alabama and Auburn sections should show "vs." not "at"
        assert "at Alabama" not in text
        assert "at Auburn" not in text
        assert "vs. Auburn" in text
        assert "vs. Alabama" in text


# ---------------------------------------------------------------------------
# fmt_schedule_result — /schedule show hint
# ---------------------------------------------------------------------------


class TestFmtScheduleResultHint:
    def test_hint_appears_when_games_scheduled(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        assert "/schedule show" in text

    def test_hint_at_end_of_output(self):
        result = SolverResult(
            assignments=[_assignment("Alabama", "Auburn", 3)],
            unscheduled=[],
        )
        text = fmt_schedule_result(result, {})
        # hint is in the last few lines
        last_lines = text.strip().split("\n")[-3:]
        assert any("/schedule show" in line for line in last_lines)

    def test_hint_absent_when_nothing_scheduled(self):
        result = SolverResult(
            assignments=[],
            unscheduled=[_req("Alabama", "Auburn")],
        )
        text = fmt_schedule_result(result, {})
        assert "/schedule show" not in text


# ---------------------------------------------------------------------------
# fmt_schedule_show — conference section
# ---------------------------------------------------------------------------


class TestFmtScheduleShowConference:
    def test_shows_header_with_team_name(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3], assignments=None)
        assert "Alabama" in text

    def test_shows_conference_weeks(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3, 5], assignments=None)
        assert "Conference" in text
        assert "1" in text
        assert "3" in text
        assert "5" in text

    def test_conference_weeks_sorted(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[9, 1, 5], assignments=None)
        conf_line = next(l for l in text.splitlines() if "Conference" in l and "game" in l)
        assert conf_line.index("1") < conf_line.index("5") < conf_line.index("9")

    def test_conference_game_count_singular(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[7], assignments=None)
        assert "Conference (1 game)" in text

    def test_conference_game_count_plural(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3, 5], assignments=None)
        assert "Conference (3 games)" in text

    def test_no_conference_schedule_shows_none_entered(self):
        text = fmt_schedule_show("Army", conference_weeks=None, assignments=None)
        assert "none entered" in text


# ---------------------------------------------------------------------------
# fmt_schedule_show — NC not yet scheduled
# ---------------------------------------------------------------------------


class TestFmtScheduleShowNcNotScheduled:
    def test_mentions_nc_not_scheduled(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3], assignments=None)
        assert "not yet scheduled" in text

    def test_hints_schedule_create(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3], assignments=None)
        assert "/schedule create" in text

    def test_no_bye_weeks_when_nc_not_scheduled(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3], assignments=None)
        assert "Bye" not in text


# ---------------------------------------------------------------------------
# fmt_schedule_show — NC scheduled
# ---------------------------------------------------------------------------


class TestFmtScheduleShow:
    def test_no_nc_games_shows_none_scheduled(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3], assignments=[])
        assert "none scheduled" in text

    def test_single_game_as_team_a(self):
        a = _assignment("Alabama", "Auburn", 5)
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=[a])
        assert "Week 5" in text
        assert "Auburn" in text

    def test_single_game_as_team_b(self):
        a = _assignment("Auburn", "Alabama", 5)
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=[a])
        assert "Week 5" in text
        assert "Auburn" in text

    def test_multiple_games_sorted_by_week(self):
        assignments = [
            _assignment("Alabama", "Georgia", 9),
            _assignment("Alabama", "Auburn", 3),
        ]
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=assignments)
        assert text.index("Week 3") < text.index("Week 9")

    def test_opponent_name_appears(self):
        a = _assignment("Alabama", "Notre Dame", 7)
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=[a])
        assert "Notre Dame" in text

    def test_nc_game_count_singular(self):
        a = _assignment("Alabama", "Auburn", 5, home_team="Alabama")
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=[a])
        assert "Non-conference (1 game)" in text

    def test_nc_game_count_plural(self):
        assignments = [
            _assignment("Alabama", "Auburn", 5, home_team="Alabama"),
            _assignment("Alabama", "Georgia", 7, home_team="Alabama"),
        ]
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=assignments)
        assert "Non-conference (2 games)" in text


class TestFmtScheduleShowHomeAway:
    def test_team_home_shows_vs(self):
        a = _assignment("Alabama", "Auburn", 3, home_team="Alabama")
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=[a])
        assert "vs. Auburn" in text

    def test_team_away_shows_at(self):
        a = _assignment("Alabama", "Auburn", 3, home_team="Auburn")
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=[a])
        assert "at Auburn" in text

    def test_unset_home_team_shows_vs(self):
        a = _assignment("Alabama", "Auburn", 3, home_team="")
        text = fmt_schedule_show("Alabama", conference_weeks=[], assignments=[a])
        assert "vs. Auburn" in text


# ---------------------------------------------------------------------------
# fmt_schedule_show — bye weeks
# ---------------------------------------------------------------------------


class TestFmtScheduleShowByeWeeks:
    def test_bye_weeks_shown_when_nc_scheduled(self):
        # Conf: 1 | NC: week 3 | Bye: 2, 4-14
        a = _assignment("Alabama", "Auburn", 3, home_team="Alabama")
        text = fmt_schedule_show("Alabama", conference_weeks=[1], assignments=[a])
        assert "Bye" in text

    def test_bye_weeks_correct_values(self):
        # Conf: 1, 2 | NC: week 3 | Bye: 4-14
        a = _assignment("Alabama", "Auburn", 3, home_team="Alabama")
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 2], assignments=[a])
        bye_line = next(l for l in text.splitlines() if "Bye" in l)
        bye_nums = [int(x) for x in bye_line.split() if x.isdigit()]
        assert bye_nums == list(range(4, 15))

    def test_no_bye_weeks_if_fully_booked(self):
        # All 14 weeks occupied — no bye line
        conf = list(range(1, 8))  # weeks 1-7
        nc = [_assignment("Alabama", f"Opp{w}", w) for w in range(8, 15)]
        text = fmt_schedule_show("Alabama", conference_weeks=conf, assignments=nc)
        assert "Bye" not in text

    def test_bye_weeks_not_shown_when_nc_not_scheduled(self):
        text = fmt_schedule_show("Alabama", conference_weeks=[1, 3], assignments=None)
        assert "Bye" not in text


# ---------------------------------------------------------------------------
# fmt_schedule_show — CPU game advice
# ---------------------------------------------------------------------------


class TestFmtScheduleShowCpuAdvice:
    def test_no_advice_when_schedule_full(self):
        # 11 conf + 1 NC = nc_cap 1, nc_scheduled 1 → 0 open slots
        assignments = [_assignment("Alabama", "Army", 12, home_team="Alabama")]
        text = fmt_schedule_show(
            "Alabama",
            conference_weeks=list(range(1, 12)),  # 11 conf weeks → nc_cap=1
            assignments=assignments,
            conference_home_games=6,
        )
        assert "Open slots" not in text

    def test_no_advice_when_nc_not_scheduled(self):
        # Solver hasn't run — home/away unknown, can't give precise advice
        text = fmt_schedule_show(
            "Alabama",
            conference_weeks=list(range(1, 9)),
            assignments=None,
            conference_home_games=4,
        )
        assert "Open slots" not in text

    def test_advice_shows_open_slot_count(self):
        # 10 conf + 0 NC = nc_cap 2, nc_scheduled 0 → 2 open slots
        text = fmt_schedule_show(
            "Alabama",
            conference_weeks=list(range(1, 11)),  # 10 conf → nc_cap=2
            assignments=[],
            conference_home_games=5,
        )
        assert "Open slots: 2" in text

    def test_balanced_advice(self):
        # 10 conf (5H 5A), 0 NC, nc_cap=2 → current 5H 5A → need 1H 1A
        text = fmt_schedule_show(
            "Alabama",
            conference_weeks=list(range(1, 11)),  # nc_cap=2
            assignments=[],
            conference_home_games=5,
        )
        assert "1 home" in text
        assert "1 away" in text

    def test_all_home_advice(self):
        # 10 conf (2H 8A), 0 NC, nc_cap=2 → current 2H 8A → need 2H 0A
        text = fmt_schedule_show(
            "Alabama",
            conference_weeks=list(range(1, 11)),  # nc_cap=2
            assignments=[],
            conference_home_games=2,
        )
        assert "2 home" in text
        assert "0 away" in text

    def test_all_away_advice(self):
        # 10 conf (8H 2A), 0 NC, nc_cap=2 → current 8H 2A → need 0H 2A
        text = fmt_schedule_show(
            "Alabama",
            conference_weeks=list(range(1, 11)),  # nc_cap=2
            assignments=[],
            conference_home_games=8,
        )
        assert "0 home" in text
        assert "2 away" in text

    def test_advice_after_bye_weeks(self):
        # CPU advice appears after bye weeks line
        # 10 conf + 0 NC → bye weeks exist, and 2 open NC slots
        text = fmt_schedule_show(
            "Alabama",
            conference_weeks=list(range(1, 11)),  # nc_cap=2
            assignments=[],
            conference_home_games=5,
        )
        assert text.index("Bye") < text.index("Open slots")


# ---------------------------------------------------------------------------
# fmt_teams
# ---------------------------------------------------------------------------


class TestFmtTeams:
    def test_shows_resolved_member_with_mention(self):
        text = fmt_teams(resolved=[("Alabama", 123)], unrecognized=[])
        assert "Alabama" in text
        assert "<@123>" in text

    def test_resolved_formatted_as_team_dash_mention(self):
        text = fmt_teams(resolved=[("Alabama", 123)], unrecognized=[])
        assert "Alabama — <@123>" in text

    def test_shows_unrecognized_member_mention(self):
        text = fmt_teams(resolved=[], unrecognized=[("RandomGuy", 999)])
        assert "<@999>" in text

    def test_unrecognized_no_display_name_prefix(self):
        text = fmt_teams(resolved=[], unrecognized=[("RandomGuy", 999)])
        assert "RandomGuy" not in text

    def test_unrecognized_sorted_alphabetically(self):
        text = fmt_teams(resolved=[], unrecognized=[("Zeke", 1), ("Aaron", 2)])
        assert text.index("<@2>") < text.index("<@1>")

    def test_resolved_sorted_alphabetically(self):
        text = fmt_teams(resolved=[("Georgia", 3), ("Alabama", 1), ("Auburn", 2)], unrecognized=[])
        assert text.index("Alabama") < text.index("Auburn") < text.index("Georgia")

    def test_members_section_header_with_count(self):
        text = fmt_teams(resolved=[("Alabama", 1), ("Auburn", 2)], unrecognized=[])
        assert "Members (2):" in text

    def test_unrecognized_section_header_with_count(self):
        text = fmt_teams(resolved=[], unrecognized=[("RandomGuy", 1), ("OtherGuy", 2)])
        assert "Unrecognized (2):" in text

    def test_no_jargon_in_output(self):
        text = fmt_teams(resolved=[], unrecognized=[("RandomGuy", 99)])
        assert "ignore_regex" not in text
        assert "unparsable" not in text.lower()

    def test_both_sections_shown(self):
        text = fmt_teams(resolved=[("Alabama", 1)], unrecognized=[("RandomGuy", 99)])
        assert "Members (1):" in text
        assert "Alabama — <@1>" in text
        assert "Unrecognized (1):" in text
        assert "<@99>" in text

    def test_empty_both_shows_fallback(self):
        text = fmt_teams(resolved=[], unrecognized=[])
        assert text


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_admin_warning_mentions_config(self):
        assert "admin.id" in ADMIN_WARNING
        assert "config/" in ADMIN_WARNING
