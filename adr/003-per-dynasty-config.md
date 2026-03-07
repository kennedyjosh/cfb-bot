# ADR-003: Per-Dynasty Configuration Storage

**Status:** Accepted  
**Date:** March 2026

---

## Context

Different dynasties may have different operational preferences — for example, the format used to extract team names from Discord display names. These settings need to be stored per-dynasty, persist across bot restarts, and be easy for an admin to read and modify without requiring database tooling or bot commands.

Options evaluated: TOML/YAML file per dynasty, `dynasty_config` table in SQLite (key-value or typed columns), JSON blob in SQLite, global `.env`-style flat file.

---

## Decision

Use a **TOML file per dynasty**, stored at `config/<guild_id>.toml`.

---

## Rationale

Human readability is the primary requirement. Config changes are infrequent — typically set once when a dynasty is established and rarely touched thereafter — so the operational overhead of a separate file is acceptable. The ability for an admin to open a text file and make a change without any tooling or bot commands is a meaningful usability advantage.

**TOML** is preferred over YAML because `tomllib` is part of the Python standard library (3.11+), adding no extra dependency, and TOML's syntax is simpler and less error-prone than YAML (no indentation-sensitive parsing, no implicit type coercion surprises).

**SQLite-based options** (key-value table, typed columns, JSON blob) were ruled out because they sacrifice human readability — inspecting or editing config requires SQLite tooling or a bot command. While keeping config co-located with dynasty data has appeal, the infrequency of config changes makes the two-source-of-truth tradeoff acceptable.

**A global flat file** was ruled out because it cannot support per-dynasty settings.

### Accepted Tradeoffs

- Config and runtime data live in separate places (TOML files vs. SQLite). This is manageable given how rarely config changes.
- No transactional safety on config writes. Acceptable given the low write frequency; a corrupt config file is recoverable by hand.
- File proliferation with many dynasties is possible but unlikely to be a practical problem at the scale of this project.

---

## Consequences

- Each dynasty gets a `config/<guild_id>.toml` file, created with defaults on first run.
- `tomllib` (read-only) is used for reads. Writes use `tomli-w` (a lightweight additional dependency) or manual file construction, since `tomllib` does not support writing.
- The canonical list of all supported config keys, their defaults, and documentation lives in `config/default.toml`. New keys are added there first.
- New per-dynasty config keys can be added without any schema migration — just add a key with a default value to `config/default.toml`.
- All config keys must have sensible defaults so that dynasties without an explicit config file still work.
- The `config/` directory should be excluded from version control (`.gitignore`) as it contains instance-specific runtime data, not code. The exception is `config/default.toml`, which should be committed.
