# ADR-002: Persistence Layer Selection

**Status:** Accepted  
**Date:** March 2026

---

## Context

Starting from Feature 3, the bot must persist data across sessions — teams, conference schedules, solved schedules, and (from Feature 5) multi-season home/away balance history and home-and-home obligations. The persistence layer must handle relational data cleanly, require minimal infrastructure, and support cross-season queries such as cumulative home/away balance per team.

Options evaluated: SQLite, JSON files, PostgreSQL/MySQL, TinyDB/shelve.

---

## Decision

Use **SQLite** via Python's standard library `sqlite3`.

---

## Rationale

The data model is inherently relational — teams belong to seasons, games link two teams, obligations reference past games — and will grow more so as multi-season features are added. This makes a relational store preferable to a flat document format.

**SQLite** fits well because:

- It is a single file on disk with zero infrastructure requirements.
- `sqlite3` is part of the Python standard library — no additional dependency.
- It handles the relational structure of the data model cleanly, including cross-season queries for cumulative balance tracking.
- It is portable and easy to back up, inspect, and debug manually.
- Concurrent write serialization (a known SQLite limitation) is a non-issue at this scale: writes are infrequent (schedule setup happens once per season) and latency from serialization would be imperceptible.

**JSON files** were ruled out because they offer no referential integrity, become unwieldy for cross-season relational queries, and are unsafe for concurrent writes. They would be adequate for Features 1–3 but would require a migration to a proper store before Feature 5.

**PostgreSQL/MySQL** were ruled out as operationally excessive. Their concurrency advantages only matter at a scale this project will not approach. Requiring a running database server adds meaningful infrastructure overhead for what is a single-instance Discord bot.

**TinyDB/shelve** were ruled out as they offer no meaningful advantage over JSON for this use case and have limited community support.

---

## Consequences

- A SQLite database file will be created on first run and must be included in backup procedures.
- Schema migrations must be written carefully as the data model evolves across features. Each migration should be versioned and applied automatically on bot startup.
- If the project is ever scaled to a hosted multi-tenant service with high write concurrency, migration to PostgreSQL should be reconsidered at that time. The SQLite schema should be written to make such a migration straightforward.
