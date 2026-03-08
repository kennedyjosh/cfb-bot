"""Tests for bot/config.py and the config data files."""

from bot.config import load_valid_teams
from bot.parsing import ABBREVIATIONS


def test_abbreviation_targets_are_valid_teams():
    """Every value in ABBREVIATIONS must be a canonical name from teams.txt."""
    valid = load_valid_teams()
    bad = {abbr: target for abbr, target in ABBREVIATIONS.items() if target not in valid}
    assert bad == {}, f"Abbreviations point to unknown teams: {bad}"
