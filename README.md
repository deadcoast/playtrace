# playtrace

A Python CLI for ingesting native Windows execution artifacts, preserving raw provenance, and rebuilding title/session views from stored evidence.

## Current Pipeline

`playtrace` now uses an evidence-first flow:

1. collect raw artifacts from Security Log, Prefetch, UserAssist, SRUM, AmCache, and BAM
2. parse them into typed evidence records
3. normalize executable identity
4. rebuild executables, sessions, and titles from persisted evidence plus mappings
5. inspect results through `report`, `inspect`, `sources`, and `doctor`

Exact runtime comes from Security Log start/exit pairs. Prefetch, UserAssist, SRUM, AmCache, and BAM remain supporting evidence.

## Commands

```bash
uv run python -m playtrace --help
uv run python -m playtrace scan --source security_log
uv run python -m playtrace report
uv run python -m playtrace inspect "Elden Ring"
uv run python -m playtrace sources eldenring.exe
uv run python -m playtrace doctor
```

## Development

Build the package with:

```bash
uv build
```

Run the full test suite with:

```bash
uv run pytest
```
