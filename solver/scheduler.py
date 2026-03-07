"""CP-SAT scheduler: assigns weeks to non-conference game requests."""

from ortools.sat.python import cp_model

from solver.model import Assignment, Request, SolverInput, SolverResult, Team

VALID_WEEKS = range(1, 15)  # Weeks 1–14


def _cpu_team(name: str) -> Team:
    return Team(name=name, conference_weeks=frozenset(), is_cpu=True)


def solve(solver_input: SolverInput) -> SolverResult:
    """
    Assign weeks to as many schedule requests as possible.

    Hard constraints:
      - Each request is assigned to at most one week.
      - No team plays more than one game per week.
      - No team is assigned a non-conference game on a conference game week.
      - No non-CPU team exceeds their nc_cap.

    Objective: maximize the number of fulfilled requests.
    """
    requests = solver_input.requests
    if not requests:
        return SolverResult(assignments=[], unscheduled=[])

    # Build the full team registry. Any team referenced in a request but
    # not in solver_input.teams is treated as a CPU team.
    teams: dict[str, Team] = dict(solver_input.teams)
    for req in requests:
        for name in (req.team_a, req.team_b):
            if name not in teams:
                teams[name] = _cpu_team(name)

    model = cp_model.CpModel()

    # Decision variables: x[r, w] = True iff request r is assigned to week w.
    # Variables are only created for weeks where neither team has a conf game.
    x: dict[tuple[int, int], cp_model.IntVar] = {}
    for r, req in enumerate(requests):
        team_a = teams[req.team_a]
        team_b = teams[req.team_b]
        blocked = team_a.conference_weeks | team_b.conference_weeks
        for w in VALID_WEEKS:
            if w not in blocked:
                x[r, w] = model.new_bool_var(f"x_{r}_{w}")

    # Constraint: each request assigned to at most one week.
    for r in range(len(requests)):
        week_vars = [x[r, w] for w in VALID_WEEKS if (r, w) in x]
        if week_vars:
            model.add(sum(week_vars) <= 1)

    # Constraint: no team plays more than one game per week (all teams).
    for team_name in teams:
        involved = [r for r, req in enumerate(requests)
                    if req.team_a == team_name or req.team_b == team_name]
        if len(involved) < 2:
            continue
        for w in VALID_WEEKS:
            week_vars = [x[r, w] for r in involved if (r, w) in x]
            if len(week_vars) > 1:
                model.add(sum(week_vars) <= 1)

    # Constraint: non-CPU teams cannot exceed their nc_cap.
    for team_name, team in teams.items():
        if team.is_cpu:
            continue
        involved = [r for r, req in enumerate(requests)
                    if req.team_a == team_name or req.team_b == team_name]
        all_vars = [x[r, w] for r in involved for w in VALID_WEEKS if (r, w) in x]
        if all_vars:
            model.add(sum(all_vars) <= team.nc_cap)

    # Objective: maximize fulfilled requests.
    model.maximize(sum(x.values()))

    solver = cp_model.CpSolver()
    status = solver.solve(model)

    assignments: list[Assignment] = []
    unscheduled: list[Request] = []

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for r, req in enumerate(requests):
            assigned_week = next(
                (w for w in VALID_WEEKS if (r, w) in x and solver.boolean_value(x[r, w])),
                None,
            )
            if assigned_week is not None:
                assignments.append(Assignment(request=req, week=assigned_week))
            else:
                unscheduled.append(req)
    else:
        unscheduled = list(requests)

    return SolverResult(assignments=assignments, unscheduled=unscheduled)
