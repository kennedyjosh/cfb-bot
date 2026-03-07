"""Pure parsing functions for the bot layer. No Discord dependency."""

import re


def parse_conf_weeks(weeks_str: str) -> list[int]:
    """Parse a space-separated string of week numbers into a sorted, deduplicated list.

    Raises ValueError with a user-facing message on invalid input.
    """
    parts = weeks_str.split()
    if not parts:
        raise ValueError("No weeks provided.")

    weeks: list[int] = []
    for part in parts:
        try:
            w = int(part)
        except ValueError:
            raise ValueError(
                "Could not parse weeks. Expected space-separated integers, e.g. '1 3 5 7'."
            )
        if not 1 <= w <= 14:
            raise ValueError(f"Week {w} is out of range. Valid weeks are 1\u201314.")
        weeks.append(w)

    return sorted(set(weeks))


def resolve_team_name(
    raw: str, nicknames: dict[str, str], valid_teams: set[str]
) -> str | None:
    """Resolve a raw extracted name to a canonical team name.

    Performs nickname lookup (case-insensitive) then validates against valid_teams.
    Returns the canonical name, or None if not found.
    """
    normalized = " ".join(raw.split())

    lower = normalized.lower()
    for nick, canonical in nicknames.items():
        if nick.lower() == lower:
            normalized = canonical
            break

    return normalized if normalized in valid_teams else None


def parse_display_name(
    display_name: str,
    name_regex: str,
    ignore_regex: str,
    nicknames: dict[str, str],
    valid_teams: set[str],
) -> tuple[str | None, bool]:
    """Parse a Discord display name into a resolved team name.

    Returns ``(team_name, is_ignored)``:

    - ``(None, True)``  — matched ``ignore_regex``; member is intentionally excluded.
    - ``(None, False)`` — regex did not match or team not in ``valid_teams``; unparsable.
    - ``(name, False)`` — successfully resolved to a canonical team name.
    """
    if re.search(ignore_regex, display_name, re.IGNORECASE):
        return None, True

    match = re.search(name_regex, display_name)
    if not match:
        return None, False

    try:
        raw = match.group("team")
    except IndexError:
        return None, False

    if not raw or not raw.strip():
        return None, False

    team = resolve_team_name(raw.strip(), nicknames, valid_teams)
    return team, False
