"""In-memory per-guild state. Not persisted across bot restarts (Feature 1)."""

from dataclasses import dataclass, field

from solver.model import Request, SolverResult


@dataclass
class GuildState:
    """All mutable scheduling state for one Discord guild."""

    conference_schedules: dict[str, set[int]] = field(default_factory=dict)
    conference_home_games: dict[str, int] = field(default_factory=dict)
    requests: list[Request] = field(default_factory=list)
    last_result: SolverResult | None = None

    def set_conference_schedule(self, team: str, weeks: list[int], home_games: int) -> bool:
        """Store or replace a team's conference schedule.

        Returns True if a prior entry was replaced, False if this is a new entry.
        """
        existed = team in self.conference_schedules
        self.conference_schedules[team] = set(weeks)
        self.conference_home_games[team] = home_games
        return existed

    def add_request(self, team1: str, team2: str) -> Request:
        """Append a new NC game request and return it."""
        req = Request(team_a=team1, team_b=team2)
        self.requests.append(req)
        return req

    def has_duplicate_request(self, team1: str, team2: str) -> bool:
        """Return True if a request for this pair already exists (either order)."""
        pair = frozenset({team1, team2})
        return any(frozenset({r.team_a, r.team_b}) == pair for r in self.requests)

    def teams_missing_conf_schedule(self, human_teams: set[str]) -> list[str]:
        """Return human teams referenced in requests but missing a conf schedule."""
        referenced = {r.team_a for r in self.requests} | {r.team_b for r in self.requests}
        human_referenced = referenced & human_teams
        return sorted(human_referenced - self.conference_schedules.keys())
