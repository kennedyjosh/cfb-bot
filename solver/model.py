"""Data models for the scheduler solver layer."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Team:
    name: str
    conference_weeks: frozenset[int] = field(default_factory=frozenset)
    is_cpu: bool = False
    conference_home_games: int = 0

    def __post_init__(self) -> None:
        for w in self.conference_weeks:
            if not 1 <= w <= 14:
                raise ValueError(f"Week {w} is out of range. Valid conference weeks are 1–14.")

    @property
    def nc_cap(self) -> int:
        """Maximum number of non-conference games this team can be assigned."""
        return 12 - len(self.conference_weeks)


@dataclass(frozen=True)
class Request:
    team_a: str
    team_b: str


@dataclass(frozen=True)
class Assignment:
    request: Request
    week: int
    home_team: str = ""


@dataclass
class SolverInput:
    teams: dict[str, Team]
    requests: list[Request]


@dataclass
class SolverResult:
    assignments: list[Assignment]
    unscheduled: list[Request]
