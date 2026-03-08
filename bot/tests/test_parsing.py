"""Tests for bot/parsing.py — pure functions, no Discord dependency."""

import pytest

from bot.parsing import parse_conf_weeks, parse_display_name, resolve_team_name


VALID_TEAMS: set[str] = {
    "Alabama",
    "Appalachian State",
    "Army",
    "Auburn",
    "BYU",
    "Florida State",
    "Georgia",
    "LSU",
    "Notre Dame",
    "North Carolina",
    "California",
}

DEFAULT_NAME_REGEX = r"^(?P<team>.+)$"
DEFAULT_IGNORE_REGEX = "inactive"


# ---------------------------------------------------------------------------
# parse_conf_weeks
# ---------------------------------------------------------------------------


class TestParseConfWeeks:
    def test_simple_list(self):
        assert parse_conf_weeks("1 3 5 7") == [1, 3, 5, 7]

    def test_single_week(self):
        assert parse_conf_weeks("7") == [7]

    def test_deduplicates(self):
        assert parse_conf_weeks("1 1 3 3") == [1, 3]

    def test_returns_sorted(self):
        assert parse_conf_weeks("9 3 1 7") == [1, 3, 7, 9]

    def test_boundary_week_1(self):
        assert parse_conf_weeks("1") == [1]

    def test_boundary_week_14(self):
        assert parse_conf_weeks("14") == [14]

    def test_extra_whitespace_is_handled(self):
        assert parse_conf_weeks("  1   3   5  ") == [1, 3, 5]

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_conf_weeks("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            parse_conf_weeks("   ")

    def test_non_integer_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            parse_conf_weeks("1 abc 3")

    def test_week_zero_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_conf_weeks("0")

    def test_week_15_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_conf_weeks("15")

    def test_negative_week_raises(self):
        with pytest.raises(ValueError, match="out of range"):
            parse_conf_weeks("-1")

    def test_mixed_valid_and_invalid_raises(self):
        with pytest.raises(ValueError):
            parse_conf_weeks("1 3 15")


# ---------------------------------------------------------------------------
# resolve_team_name
# ---------------------------------------------------------------------------


class TestResolveTeamName:
    def test_exact_match(self):
        assert resolve_team_name("Alabama", VALID_TEAMS) == "Alabama"

    def test_exact_match_multiword(self):
        assert resolve_team_name("Appalachian State", VALID_TEAMS) == "Appalachian State"

    def test_abbreviation_app_state(self):
        assert resolve_team_name("App State", VALID_TEAMS) == "Appalachian State"

    def test_abbreviation_bama(self):
        assert resolve_team_name("Bama", VALID_TEAMS) == "Alabama"

    def test_abbreviation_case_insensitive(self):
        assert resolve_team_name("app state", VALID_TEAMS) == "Appalachian State"
        assert resolve_team_name("APP STATE", VALID_TEAMS) == "Appalachian State"

    def test_abbreviation_mixed_case(self):
        assert resolve_team_name("bama", VALID_TEAMS) == "Alabama"

    def test_abbreviation_unc(self):
        assert resolve_team_name("UNC", VALID_TEAMS) == "North Carolina"

    def test_abbreviation_cal(self):
        assert resolve_team_name("Cal", VALID_TEAMS) == "California"

    def test_team_name_case_insensitive_fallback(self):
        # "alabama" (lowercase) should resolve even without an abbreviation entry
        assert resolve_team_name("alabama", VALID_TEAMS) == "Alabama"

    def test_team_name_case_insensitive_multiword(self):
        assert resolve_team_name("notre dame", VALID_TEAMS) == "Notre Dame"

    def test_punctuation_stripped(self):
        assert resolve_team_name("Oregon+", VALID_TEAMS | {"Oregon"}) == "Oregon"

    def test_punctuation_stripped_period(self):
        assert resolve_team_name("Alabama.", VALID_TEAMS) == "Alabama"

    def test_mascot_not_resolved(self):
        # "Noles" was removed — mascot abbreviations are not supported
        assert resolve_team_name("Noles", VALID_TEAMS) is None

    def test_unknown_team_returns_none(self):
        assert resolve_team_name("Harvard", VALID_TEAMS) is None

    def test_unknown_abbreviation_not_in_teams_returns_none(self):
        assert resolve_team_name("Crimson Tide", VALID_TEAMS) is None

    def test_internal_whitespace_normalized(self):
        assert resolve_team_name("App  State", VALID_TEAMS) == "Appalachian State"

    def test_empty_valid_teams(self):
        assert resolve_team_name("Alabama", set()) is None


# ---------------------------------------------------------------------------
# parse_display_name
# ---------------------------------------------------------------------------


class TestParseDisplayName:
    def _parse(self, display_name: str, *, name_regex=DEFAULT_NAME_REGEX) -> tuple:
        return parse_display_name(
            display_name, name_regex, DEFAULT_IGNORE_REGEX, VALID_TEAMS
        )

    def test_simple_team_name(self):
        team, ignored = self._parse("Alabama")
        assert team == "Alabama"
        assert ignored is False

    def test_abbreviation_resolved(self):
        team, ignored = self._parse("App State")
        assert team == "Appalachian State"
        assert ignored is False

    def test_ignored_lowercase(self):
        team, ignored = self._parse("Josh (inactive)")
        assert team is None
        assert ignored is True

    def test_ignored_uppercase(self):
        team, ignored = self._parse("INACTIVE Player")
        assert team is None
        assert ignored is True

    def test_ignored_mixed_case(self):
        team, ignored = self._parse("Player [Inactive]")
        assert team is None
        assert ignored is True

    def test_unparsable_unknown_team(self):
        team, ignored = self._parse("Harvard")
        assert team is None
        assert ignored is False

    def test_custom_name_regex_bracket_format(self):
        team, ignored = parse_display_name(
            "[Alabama] Josh",
            r"\[(?P<team>[^\]]+)\]",
            DEFAULT_IGNORE_REGEX,
            VALID_TEAMS,
        )
        assert team == "Alabama"
        assert ignored is False

    def test_custom_name_regex_no_match(self):
        team, ignored = parse_display_name(
            "Josh",
            r"\[(?P<team>[^\]]+)\]",
            DEFAULT_IGNORE_REGEX,
            VALID_TEAMS,
        )
        assert team is None
        assert ignored is False

    def test_custom_name_regex_abbreviation_via_bracket(self):
        team, ignored = parse_display_name(
            "[App State] Josh",
            r"\[(?P<team>[^\]]+)\]",
            DEFAULT_IGNORE_REGEX,
            VALID_TEAMS,
        )
        assert team == "Appalachian State"
        assert ignored is False

    def test_ignore_takes_priority_over_unparsable_name(self):
        # Even if the name wouldn't resolve, ignore_regex fires first
        team, ignored = self._parse("Harvard [Inactive]")
        assert team is None
        assert ignored is True

    def test_ignore_regex_does_not_match_partial_word_contained(self):
        # "activate" contains "active" but not "inactive"
        team, ignored = self._parse("activate")
        assert ignored is False

    def test_whitespace_only_display_name_is_unparsable(self):
        team, ignored = self._parse("   ")
        assert team is None
        assert ignored is False

    def test_multiword_team_name_resolved(self):
        team, ignored = self._parse("Notre Dame")
        assert team == "Notre Dame"
        assert ignored is False

    def test_custom_ignore_regex(self):
        team, ignored = parse_display_name(
            "Bot Account",
            DEFAULT_NAME_REGEX,
            r"bot",
            VALID_TEAMS,
        )
        assert team is None
        assert ignored is True
