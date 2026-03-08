"""Config loading for the CFB bot. Merges default.toml with per-guild overrides."""

import tomllib
from pathlib import Path

_CONFIG_DIR = Path(__file__).parent.parent / "config"
_DEFAULT_TOML = _CONFIG_DIR / "default.toml"
_TEAMS_TXT = Path(__file__).parent.parent / "teams.txt"


def load_defaults() -> dict:
    with open(_DEFAULT_TOML, "rb") as f:
        return tomllib.load(f)


def load_guild_config(guild_id: int) -> dict:
    """Load merged config for a guild: defaults overlaid with guild-specific overrides."""
    config = load_defaults()
    guild_path = _CONFIG_DIR / f"{guild_id}.toml"
    if guild_path.exists():
        with open(guild_path, "rb") as f:
            overrides = tomllib.load(f)
        _deep_merge(config, overrides)
    return config


def _deep_merge(base: dict, overrides: dict) -> None:
    """Merge overrides into base in-place (one level deep for nested dicts)."""
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def load_valid_teams() -> set[str]:
    """Load the set of valid canonical team names from teams.txt."""
    with open(_TEAMS_TXT) as f:
        return {line.strip() for line in f if line.strip()}
