# Repository Guidelines

## Project Structure & Module Organization
`playtrace/` contains the application package. Keep new code in the layer that matches its job: `cli/` for Typer commands, `services/` for orchestration, `parsers/` for Windows artifact readers, `normalize/`, `classify/`, and `merge/` for domain logic, `store/` for SQLite access, `render/` for Rich output, `models/` for shared dataclasses and enums, and `utils/` for low-level helpers. `tests/` should mirror the package areas they cover. `docs/` holds product and scaffold notes, and `tools/bootstrap_playtrace.py` is the project bootstrap script.

## Build, Test, and Development Commands
Use `uv` from the repository root.

- `uv build` builds the distribution from `pyproject.toml`.
- `uv run pytest` runs the test suite under `tests/`.
- `uv run python -m playtrace --help` shows the CLI surface.
- `uv run python -m playtrace report --db playtrace.db` exercises the default report flow against a local database.

## Coding Style & Naming Conventions
Target Python 3.12 and keep 4-space indentation. Follow the existing typed style: most modules start with `from __future__ import annotations`, public data containers use `@dataclass(slots=True)`, and functions and modules use `snake_case` while classes use `PascalCase`. Group imports as standard library, third-party, then local package imports. Keep CLI handlers thin and move business logic into `services/` or the relevant domain package.

## Testing Guidelines
Use `pytest`. Name files `tests/test_<area>.py` and test functions `test_<behavior>()`. When you change parser, merge, classification, store, or render behavior, add tests in the matching area instead of relying on manual verification. The checked-in test modules are still placeholders, and `uv run pytest` currently collects zero real tests, so new work should add concrete behavioral assertions.

## Commit & Pull Request Guidelines
Recent commits use short imperative subjects such as `Implement initial database schema...` and `Refactor code structure...`. Keep commits focused, use imperative mood, and avoid mixing refactors with behavior changes. PRs should summarize the affected pipeline or CLI commands, list validation steps run locally, and include terminal screenshots when Rich report output changes. Link the relevant issue or design note in `docs/` when applicable.
