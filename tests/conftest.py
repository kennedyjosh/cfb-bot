"""Shared fixtures for integration tests."""

import pytest

from bot.state import GuildState


@pytest.fixture
def dynasty_state():
    """
    Realistic 4-team dynasty: Alabama, Auburn, Georgia (human) + Purdue (CPU).

    Conference schedules are interleaved so each pair has open weeks together:
      Alabama blocked: 1,3,5,7,9,11  → open: 2,4,6,8,10,12,13,14
      Auburn  blocked: 2,4,6,8,10,12 → open: 1,3,5,7,9,11,13,14
      Georgia blocked: 1,2,3,4,5,6   → open: 7,8,9,10,11,12,13,14

    Requests (all fulfillable):
      Alabama vs. Auburn   (common open: 13,14)
      Alabama vs. Georgia  (common open: 8,10,12,13,14)
      Auburn  vs. Georgia  (common open: 7,9,11,13,14)
      Alabama vs. Purdue   (Purdue is CPU; Alabama open: 2,4,6,8,10,12,13,14)
    """
    state = GuildState()
    state.set_conference_schedule("Alabama", [1, 3, 5, 7, 9, 11], 3)   # nc_cap=6
    state.set_conference_schedule("Auburn",  [2, 4, 6, 8, 10, 12], 3)  # nc_cap=6
    state.set_conference_schedule("Georgia", [1, 2, 3, 4, 5, 6], 3)    # nc_cap=6
    state.add_request("Alabama", "Auburn")
    state.add_request("Alabama", "Georgia")
    state.add_request("Auburn", "Georgia")
    state.add_request("Alabama", "Purdue")   # Purdue auto-registered as CPU
    return state
