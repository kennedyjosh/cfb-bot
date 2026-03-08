"""Tests for pure helper functions extracted from bot/main.py."""

import pytest

from solver.model import SolverResult
from bot.state import GuildState
from bot.main import ResolvedMember, UnresolvedMember, process_member_display_name, handle_member_display_name_change


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

    def test_invalid_name_regex_raises_value_error(self):
        with pytest.raises(ValueError):
            process_member_display_name(
                display_name="Alabama",
                user_id=1,
                name_regex="[invalid",
                ignore_regex=IGNORE_REGEX,
                valid_teams=VALID_TEAMS,
            )


def _mock_result() -> SolverResult:
    return SolverResult(assignments=[], unscheduled=[])


def _make_resolved(display_name: str, team: str, user_id: int) -> ResolvedMember:
    return ResolvedMember(display_name=display_name, team=team, user_id=user_id)


def _make_unresolved(display_name: str, user_id: int, is_ignored: bool = False) -> UnresolvedMember:
    return UnresolvedMember(display_name=display_name, user_id=user_id, is_ignored=is_ignored)


class TestHandleMemberDisplayNameChange:
    GUILD_ID = 100
    USER_ID = 42

    # --- Permutation 1: resolved → resolved (same team, no-op rename) ---
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

        # member stays resolved with same team
        assert human_teams == {"Alabama": self.USER_ID}
        assert len(resolved) == 1
        assert resolved[0].team == "Alabama"
        assert unresolved == []
        # conf schedule and requests unchanged (rename_team is idempotent for same team)
        assert "Alabama" in state.conference_schedules
        assert "Alabama" in state.conference_home_games
        assert len(state.requests) == 1
        # last_result nulled (rename_team always nulls it)
        assert state.last_result is None

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
        # conf schedule cleared for Alabama
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
        state.set_conference_schedule("Georgia", [1, 2], home_games=1)  # NOTE: added vs plan
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
        # Georgia's data untouched (no old team to clear)
        assert "Georgia" in state.conference_schedules
        assert "Georgia" in state.conference_home_games
        assert len(state.requests) == 1
        # last_result unchanged (no scheduling state changed)
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
        assert "Georgia" in state.conference_home_games
        assert len(state.requests) == 1
        assert state.last_result is not None
