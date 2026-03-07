# ADR-001: Language and Solver Selection

**Status:** Accepted  
**Date:** March 2026

---

## Context

The CFB 26 Dynasty Scheduler requires two core capabilities: a Discord bot interface and a combinatorial optimization solver. The language and solver choices are tightly coupled — OR-Tools, the leading open-source constraint solver, has official bindings only for Python, Java, C#, and C++. The choice of language therefore determines which solver options are available.

Languages evaluated: Python, TypeScript/Node.js, Elixir, Go.

---

## Decision

Use **Python** with **Google OR-Tools (CP-SAT)** as the solver, and **discord.py** as the Discord library.

---

## Rationale

### Language

Python was selected over the alternatives for the following reasons:

- OR-Tools has its best-supported, most thoroughly documented bindings in Python. This is the decisive factor.
- `discord.py` is a mature, well-maintained library with strong slash command support.
- Python's `asyncio` handles concurrent Discord interactions cleanly at the scale of this project (up to 32 users).
- The codebase will be logic-heavy; Python's readability is an asset for long-term maintainability.

**TypeScript/Node.js** was ruled out because OR-Tools has no official JavaScript bindings, which would require hand-rolling the solver — the most critical and complex part of the project.

**Elixir** was considered for its concurrency model and pattern matching, but ruled out because: the Nostrum Discord library is less mature than discord.py; no OR-Tools bindings exist; and the concurrency advantages Elixir offers are irrelevant at 32-user scale.

**Go** was ruled out due to verbosity, lack of a solver ecosystem, and poor ergonomics for a logic-heavy domain model.

### Solver

OR-Tools CP-SAT was selected over alternatives (python-constraint, PuLP, hand-rolled greedy/backtracking) for the following reasons:

- Guarantees an optimal solution — no valid schedule that fulfills more requests will ever be missed.
- Natively supports multi-objective optimization, allowing "maximize fulfilled requests" and "minimize home/away imbalance" to coexist in a single weighted solver run.
- Handles the full roadmap without model changes — hard constraints, soft constraints, carry-forward balance offsets, and home-and-home obligations all fit cleanly into the CP-SAT model.
- At this problem's scale (up to 32 teams, ~16 requests, 14 weeks), solve time is in the milliseconds.
- Battle-tested at production scale with thorough Python documentation.

---

## Consequences

- The project is Python-only. Contributors must be comfortable with Python and `asyncio`.
- OR-Tools must be listed as an explicit dependency (`ortools` via pip).
- The solver layer must remain cleanly separated from the Discord layer so it can be tested independently.
- If the project ever needs to be rewritten in another language, the absence of OR-Tools bindings in most languages means the solver would need to be hand-rolled or replaced with a language-native alternative.
