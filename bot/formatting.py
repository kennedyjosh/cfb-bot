"""Pure formatting functions for bot command responses. No Discord dependency."""

from solver.model import Assignment, Request, SolverResult, Team


def fmt_cpu_team_rejected(team: str) -> str:
    """Error response when a CPU team is given to /conference_schedule."""
    return f"{team} is a CPU team. Conference schedules can only be set for human-controlled teams."


def fmt_conf_schedule_set(team: str, weeks: list[int], *, home_games: int, updated: bool) -> str:
    """Response for a successful /conference_schedule command."""
    verb = "Updated" if updated else "Set"
    weeks_str = " ".join(str(w) for w in sorted(weeks))
    return (
        f"{verb} conference schedule for {team}.\n"
        f"{team}: conference games on weeks {weeks_str} ({home_games} home)."
    )


def fmt_request_added(team1: str, team2: str, index: int, total: int) -> str:
    """Response for a successful /request add command."""
    return f"Request added: {team1} vs. {team2}. (Request #{index} of {total})"


def fmt_request_removed(team1: str, team2: str) -> str:
    """Response for a successful /request remove command."""
    return f"Request removed: {team1} vs. {team2}."


def _unscheduled_reason(
    req: Request,
    teams: dict[str, Team],
    assignments: list[Assignment],
) -> str:
    """Infer why a request could not be scheduled (best-effort heuristic)."""
    valid_weeks = set(range(1, 15))
    team_a = teams.get(req.team_a)
    team_b = teams.get(req.team_b)
    blocked_a = team_a.conference_weeks if team_a else frozenset()
    blocked_b = team_b.conference_weeks if team_b else frozenset()
    if not (valid_weeks - blocked_a - blocked_b):
        return "no common open week"
    for name, team in [(req.team_a, team_a), (req.team_b, team_b)]:
        if team and not team.is_cpu:
            assigned_count = sum(
                1 for a in assignments
                if a.request.team_a == name or a.request.team_b == name
            )
            if assigned_count >= team.nc_cap:
                return f"{name}'s schedule is full"
    return "scheduling conflict"


def _home_away_counts(
    team_name: str,
    team: Team,
    assignments: list[Assignment],
) -> tuple[int, int]:
    """Return (total_home, total_away) across conference and NC games."""
    nc_games = [
        a for a in assignments
        if a.request.team_a == team_name or a.request.team_b == team_name
    ]
    nc_home = sum(1 for a in nc_games if a.home_team == team_name)
    nc_away = len(nc_games) - nc_home
    conf_away = len(team.conference_weeks) - team.conference_home_games
    return team.conference_home_games + nc_home, conf_away + nc_away


def fmt_schedule_result(result: SolverResult, teams: dict[str, Team]) -> str:
    """Format the full schedule result for /schedule create."""
    total = len(result.assignments) + len(result.unscheduled)
    fulfilled = len(result.assignments)
    lines = [f"Schedule Results \u2014 {fulfilled} of {total} requests fulfilled"]

    # Not-scheduled section (with reasons)
    if result.unscheduled:
        lines.append("")
        lines.append(f"Not scheduled ({len(result.unscheduled)}):")
        for req in result.unscheduled:
            reason = _unscheduled_reason(req, teams, result.assignments)
            lines.append(f"  {req.team_a} vs. {req.team_b} \u2014 {reason}")

    # Home/away imbalance section
    imbalanced = []
    for team_name, team in sorted(teams.items()):
        home, away = _home_away_counts(team_name, team, result.assignments)
        diff = home - away
        if abs(diff) >= 2:
            direction = "home" if diff > 0 else "away"
            imbalanced.append(f"  {team_name}: {home}H {away}A (+{abs(diff)} {direction})")
    if imbalanced:
        lines.append("")
        lines.append("Home/away imbalance:")
        lines.extend(imbalanced)

    # Per-team schedule
    if result.assignments:
        team_games: dict[str, list[Assignment]] = {}
        for a in result.assignments:
            team_games.setdefault(a.request.team_a, []).append(a)
            team_games.setdefault(a.request.team_b, []).append(a)

        lines.append("")
        lines.append("Non-conference schedule:")
        for team_name in sorted(team_games):
            games = sorted(team_games[team_name], key=lambda a: a.week)
            n = len(games)
            lines.append(f"\n{team_name} ({n} game{'s' if n != 1 else ''}):")
            for a in games:
                opponent = a.request.team_b if a.request.team_a == team_name else a.request.team_a
                if a.home_team == team_name:
                    lines.append(f"  Week {a.week}: vs. {opponent}")
                elif a.home_team == opponent:
                    lines.append(f"  Week {a.week}: at {opponent}")
                else:
                    lines.append(f"  Week {a.week}: vs. {opponent}")

        lines.append("")
        lines.append("Use /schedule show <team> to view a single team's schedule.")

    return "\n".join(lines)


def fmt_schedule_show(team: str, assignments: list[Assignment]) -> str:
    """Format the per-team schedule for /schedule show."""
    if not assignments:
        return f"{team} has no non-conference games scheduled."

    sorted_assignments = sorted(assignments, key=lambda a: a.week)
    lines = [f"Non-conference schedule for {team}:"]
    for a in sorted_assignments:
        opponent = a.request.team_b if a.request.team_a == team else a.request.team_a
        if a.home_team == team:
            lines.append(f"  Week {a.week}: vs. {opponent}")
        elif a.home_team == opponent:
            lines.append(f"  Week {a.week}: at {opponent}")
        else:
            # home_team not set — fall back to neutral display
            lines.append(f"  Week {a.week}: vs. {opponent}")

    return "\n".join(lines)


def fmt_teams(
    resolved: list[tuple[str, int]],
    unrecognized: list[tuple[str, int]],
) -> str:
    """Format the /teams response listing all members."""
    lines = []

    if resolved:
        lines.append(f"Members ({len(resolved)}):")
        for team, user_id in sorted(resolved):
            lines.append(f"  {team} — <@{user_id}>")

    if unrecognized:
        if lines:
            lines.append("")
        lines.append(f"Unrecognized ({len(unrecognized)}):")
        for name, user_id in sorted(unrecognized):
            lines.append(f"  <@{user_id}>")

    if not lines:
        lines.append("No members found.")

    return "\n".join(lines)


ADMIN_WARNING = (
    "Warning: No admin is configured for this server. "
    "All commands are currently unrestricted. "
    "Set `admin.id` in `config/<guild_id>.toml` to restrict admin access."
)

NO_PERMISSION = "You do not have permission to use this command."
