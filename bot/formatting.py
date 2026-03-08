"""Pure formatting functions for bot command responses. No Discord dependency."""

from solver.model import Assignment, Request, SolverResult


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


def fmt_schedule_result(result: SolverResult) -> str:
    """Format the full schedule result for /schedule."""
    total = len(result.assignments) + len(result.unscheduled)
    fulfilled = len(result.assignments)

    lines = [f"Schedule Results \u2014 {fulfilled} of {total} requests fulfilled", ""]

    lines.append("Fulfilled:")
    if not result.assignments:
        lines.append("  (none)")
    else:
        sorted_assignments = sorted(
            result.assignments,
            key=lambda a: (a.week, a.request.team_a),
        )
        for a in sorted_assignments:
            if a.home_team and a.home_team == a.request.team_b:
                # team_b is home: show "team_a at team_b"
                lines.append(f"  Week {a.week}: {a.request.team_a} at {a.request.team_b}")
            else:
                # team_a is home (or home_team not set): show "team_a vs. team_b"
                lines.append(f"  Week {a.week}: {a.request.team_a} vs. {a.request.team_b}")

    if result.unscheduled:
        lines.append("")
        lines.append("Not scheduled:")
        for r in result.unscheduled:
            lines.append(f"  {r.team_a} vs. {r.team_b}")

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
