"""Pure parsing functions for the bot layer. No Discord dependency."""

import re


# Unambiguous shorthand that always refers to one specific school.
# Abbreviations of school/city/state names only — not mascot names.
ABBREVIATIONS: dict[str, str] = {
    "App State": "Appalachian State",
    "Bama": "Alabama",
    "BC": "Boston College",
    "Cal": "California",
    "Cuse": "Syracuse",
    "GT": "Georgia Tech",
    "ND": "Notre Dame",
    "Pitt": "Pittsburgh",
    "TAMU": "Texas A&M",
    "UNC": "North Carolina",
    "WVU": "West Virginia",
}


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


def resolve_team_name(raw: str, valid_teams: set[str]) -> str | None:
    """Resolve a raw extracted name to a canonical team name.

    1. Normalize whitespace and strip punctuation.
    2. Check ABBREVIATIONS (case-insensitive).
    3. Exact match against valid_teams.
    4. Case-insensitive fallback against valid_teams.

    Returns the canonical name, or None if not found.
    """
    # Normalize whitespace
    normalized = " ".join(raw.split())
    # Strip punctuation (keep letters, digits, spaces, ampersand)
    cleaned = re.sub(r"[^\w\s&]", "", normalized).strip()

    # Abbreviation lookup (case-insensitive)
    lower = cleaned.lower()
    for abbr, canonical in ABBREVIATIONS.items():
        if abbr.lower() == lower:
            cleaned = canonical
            break

    # Exact match
    if cleaned in valid_teams:
        return cleaned

    # Case-insensitive fallback
    lower_cleaned = cleaned.lower()
    for team in valid_teams:
        if team.lower() == lower_cleaned:
            return team

    return None


def parse_display_name(
    display_name: str,
    name_regex: str,
    ignore_regex: str,
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

    team = resolve_team_name(raw.strip(), valid_teams)
    return team, False
