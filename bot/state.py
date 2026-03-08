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

    def remove_request(self, team1: str, team2: str) -> bool:
        """Remove the request matching the given pair (order-insensitive).

        Returns True if found and removed, False if not found.
        """
        pair = frozenset({team1, team2})
        for i, r in enumerate(self.requests):
            if frozenset({r.team_a, r.team_b}) == pair:
                self.requests.pop(i)
                return True
        return False

    def remove_requests(self, team: str) -> list[Request]:
        """Remove all requests involving ``team``. Returns the removed requests."""
        kept: list[Request] = []
        removed: list[Request] = []
        for r in self.requests:
            if r.team_a == team or r.team_b == team:
                removed.append(r)
            else:
                kept.append(r)
        self.requests = kept
        return removed

    def rename_team(self, old_team: str, new_team: str) -> dict:
        """Rename a team: clear their conf schedule, remap their requests, null last_result.

        If old_team == new_team, this is a no-op for schedule/requests but still nulls last_result.
        Returns {"removed": int, "readded": int, "skipped": int}.
        """
        if old_team == new_team:
            self.last_result = None
            return {"removed": 0, "readded": 0, "skipped": 0}

        # Clear conference schedule
        self.conference_schedules.pop(old_team, None)
        self.conference_home_games.pop(old_team, None)

        # Remap requests
        removed = self.remove_requests(old_team)
        readded = 0
        skipped = 0
        for r in removed:
            new_a = new_team if r.team_a == old_team else r.team_a
            new_b = new_team if r.team_b == old_team else r.team_b
            if self.has_duplicate_request(new_a, new_b):
                skipped += 1
            else:
                self.add_request(new_a, new_b)
                readded += 1

        self.last_result = None
        return {"removed": len(removed), "readded": readded, "skipped": skipped}

    def teams_missing_conf_schedule(self, human_teams: set[str]) -> list[str]:
        """Return human teams referenced in requests but missing a conf schedule."""
        referenced = {r.team_a for r in self.requests} | {r.team_b for r in self.requests}
        human_referenced = referenced & human_teams
        return sorted(human_referenced - self.conference_schedules.keys())
