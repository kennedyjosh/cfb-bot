# ADR-004: Testing Strategy

**Status:** Accepted  
**Date:** March 2026

---

## Context

The project has three distinct layers — `solver/`, `bot/`, and `db/` — each with different testing needs and dependencies. The solver is the most critical layer and must be tested exhaustively. The bot layer is the least critical to test directly. A consistent, low-overhead testing strategy is needed that reinforces layer separation and scales cleanly as the codebase grows.

---

## Decision

Use **pytest** as the sole test framework. Tests live within each layer's subfolder. Coverage is tracked but not enforced. Test data is inline for small cases and in a `fixtures/` folder for larger ones.

---

## Rationale

### Framework: pytest only

pytest is the standard choice for modern Python projects. Its fixture system, expressive assertions, and parametrize support are well-suited to the solver's combinatorial test cases. There is no reason to maintain `unittest` compatibility — pytest runs `unittest`-style tests anyway if needed, but no new tests should be written in that style.

### Test location: within each layer's subfolder

Each layer gets a `tests/` subdirectory:

```
solver/
  tests/
    conftest.py
    test_solver.py
bot/
  tests/
    conftest.py
    test_bot.py
db/
  tests/
    conftest.py
    test_db.py
```

This reinforces the layer separation established in the architecture: solver tests have no knowledge of the bot, db tests have no knowledge of the solver. Each subdirectory has its own `conftest.py` for layer-specific fixtures. There is no global `conftest.py` at the project root.

### Coverage: tracked, not enforced

`pytest-cov` is included as a dev dependency and coverage is reported on every test run. No minimum threshold is enforced — enforcing a number tends to incentivize writing low-value tests to hit the target. Instead, coverage reports are used as a signal to identify untested areas during code review.

### Test data: inline for small, `fixtures/` for large

Simple cases (a team with one conference game, a single request) are defined inline in the test file. Realistic multi-team, multi-week schedule scenarios that would clutter the test file live in a `fixtures/` folder within the relevant `tests/` directory. There is no prescribed format for fixture files — use whatever is most readable for the data being represented (Python dicts, TOML, JSON).

---

## What to test

**Test thoroughly:**
- Solver correctness: known inputs must produce known optimal outputs.
- Constraint enforcement: each hard constraint must be verified under adversarial inputs.
- Edge cases: no valid week exists; a team's cap is zero; all requests conflict; a team appears in multiple requests.
- DB reads/writes: data round-trips correctly; schema migrations apply cleanly.
- Bot layer logic: argument parsing, input validation, and any other non-trivial logic in the bot layer (see below).

**Bot layer testing approach:**

Command handlers should be kept as thin as possible — they receive Discord input, call a pure function, and return a response. Any non-trivial logic (argument parsing, input validation, response formatting) must be extracted into plain Python functions with no Discord dependency, and those functions must be tested like any other unit.

For example, the argument parsing for `/conference_schedule` should live in a standalone function `parse_conf_args(weeks_str, home_games) -> ConferenceSchedule` that is tested directly. The command handler itself just calls that function and passes the result to the db layer — no test needed for the wiring itself.

The only untested surface area in the bot layer should be the Discord framework wiring: registering commands, receiving interactions, and sending responses. This is framework code, not application code, and is an acceptable testing gap.

**Do not test:**
- Trivial string formatting or message construction with no branching logic.

---

## Consequences

- `pytest` and `pytest-cov` are added as dev dependencies (e.g. in `requirements-dev.txt`).
- Tests are run with `pytest` from the project root, which discovers all `tests/` subdirectories automatically.
- Coverage is reported with `pytest --cov` and reviewed as part of each feature's completion, but no CI gate is enforced on the number.
- The testing philosophy section in `CLAUDE.md` defers to this ADR for detail.
