"""Tests for bot/config.py and the config data files."""

import tomllib
from pathlib import Path


NICKNAMES_TOML = Path(__file__).parent.parent.parent / "config" / "nicknames.toml"


def test_nicknames_toml_loads_without_error():
    """nicknames.toml must be valid TOML with no duplicate keys."""
    with open(NICKNAMES_TOML, "rb") as f:
        data = tomllib.load(f)
    assert "nicknames" in data


def test_nicknames_toml_no_duplicate_keys():
    """Manually scan for duplicate keys since tomllib silently drops them or errors."""
    # tomllib already errors on duplicates, so if test_nicknames_toml_loads_without_error
    # passes, there are no duplicates. This test double-checks by scanning raw text.
    lines = NICKNAMES_TOML.read_text().splitlines()
    keys_seen = []
    duplicates = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#"):
            key = stripped.split("=")[0].strip().strip('"')
            if key in keys_seen:
                duplicates.append(key)
            keys_seen.append(key)
    assert duplicates == [], f"Duplicate nickname keys found: {duplicates}"
