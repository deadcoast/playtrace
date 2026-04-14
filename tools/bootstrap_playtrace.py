from pathlib import Path

PROJECT_ROOT = Path("playtrace")

DIRECTORIES = [
    PROJECT_ROOT,
    PROJECT_ROOT / "playtrace",
    PROJECT_ROOT / "playtrace" / "cli",
    PROJECT_ROOT / "playtrace" / "config",
    PROJECT_ROOT / "playtrace" / "models",
    PROJECT_ROOT / "playtrace" / "parsers",
    PROJECT_ROOT / "playtrace" / "ingest",
    PROJECT_ROOT / "playtrace" / "normalize",
    PROJECT_ROOT / "playtrace" / "classify",
    PROJECT_ROOT / "playtrace" / "merge",
    PROJECT_ROOT / "playtrace" / "store",
    PROJECT_ROOT / "playtrace" / "render",
    PROJECT_ROOT / "playtrace" / "services",
    PROJECT_ROOT / "playtrace" / "utils",
    PROJECT_ROOT / "tests",
    PROJECT_ROOT / "tests" / "fixtures",
]

FILES = [
    PROJECT_ROOT / "pyproject.toml",
    PROJECT_ROOT / "README.md",
    PROJECT_ROOT / ".gitignore",

    PROJECT_ROOT / "playtrace" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "__main__.py",
    PROJECT_ROOT / "playtrace" / "version.py",

    PROJECT_ROOT / "playtrace" / "cli" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "cli" / "app.py",
    PROJECT_ROOT / "playtrace" / "cli" / "common.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_scan.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_report.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_titles.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_sessions.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_inspect.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_map.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_doctor.py",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_export.py",

    PROJECT_ROOT / "playtrace" / "config" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "config" / "loader.py",
    PROJECT_ROOT / "playtrace" / "config" / "models.py",

    PROJECT_ROOT / "playtrace" / "models" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "models" / "enums.py",
    PROJECT_ROOT / "playtrace" / "models" / "artifacts.py",
    PROJECT_ROOT / "playtrace" / "models" / "executable.py",
    PROJECT_ROOT / "playtrace" / "models" / "session.py",
    PROJECT_ROOT / "playtrace" / "models" / "title.py",
    PROJECT_ROOT / "playtrace" / "models" / "mapping.py",
    PROJECT_ROOT / "playtrace" / "models" / "report.py",

    PROJECT_ROOT / "playtrace" / "parsers" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "parsers" / "base.py",
    PROJECT_ROOT / "playtrace" / "parsers" / "security_log.py",
    PROJECT_ROOT / "playtrace" / "parsers" / "prefetch.py",
    PROJECT_ROOT / "playtrace" / "parsers" / "userassist.py",
    PROJECT_ROOT / "playtrace" / "parsers" / "srum.py",
    PROJECT_ROOT / "playtrace" / "parsers" / "amcache.py",
    PROJECT_ROOT / "playtrace" / "parsers" / "bam.py",

    PROJECT_ROOT / "playtrace" / "ingest" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "ingest" / "orchestrator.py",
    PROJECT_ROOT / "playtrace" / "ingest" / "registry.py",

    PROJECT_ROOT / "playtrace" / "normalize" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "normalize" / "identity.py",
    PROJECT_ROOT / "playtrace" / "normalize" / "pathing.py",
    PROJECT_ROOT / "playtrace" / "normalize" / "metadata.py",

    PROJECT_ROOT / "playtrace" / "classify" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "classify" / "rules.py",
    PROJECT_ROOT / "playtrace" / "classify" / "heuristics.py",
    PROJECT_ROOT / "playtrace" / "classify" / "resolver.py",

    PROJECT_ROOT / "playtrace" / "merge" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "merge" / "events.py",
    PROJECT_ROOT / "playtrace" / "merge" / "sessions.py",
    PROJECT_ROOT / "playtrace" / "merge" / "titles.py",
    PROJECT_ROOT / "playtrace" / "merge" / "confidence.py",

    PROJECT_ROOT / "playtrace" / "store" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "store" / "db.py",
    PROJECT_ROOT / "playtrace" / "store" / "schema.py",
    PROJECT_ROOT / "playtrace" / "store" / "repositories.py",
    PROJECT_ROOT / "playtrace" / "store" / "migrations.py",

    PROJECT_ROOT / "playtrace" / "render" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "render" / "console.py",
    PROJECT_ROOT / "playtrace" / "render" / "theme.py",
    PROJECT_ROOT / "playtrace" / "render" / "tables.py",
    PROJECT_ROOT / "playtrace" / "render" / "cards.py",
    PROJECT_ROOT / "playtrace" / "render" / "badges.py",
    PROJECT_ROOT / "playtrace" / "render" / "timeline.py",
    PROJECT_ROOT / "playtrace" / "render" / "report_views.py",

    PROJECT_ROOT / "playtrace" / "services" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "services" / "scanner.py",
    PROJECT_ROOT / "playtrace" / "services" / "reporter.py",
    PROJECT_ROOT / "playtrace" / "services" / "mapper.py",
    PROJECT_ROOT / "playtrace" / "services" / "inspector.py",
    PROJECT_ROOT / "playtrace" / "services" / "doctor.py",
    PROJECT_ROOT / "playtrace" / "services" / "exporter.py",

    PROJECT_ROOT / "playtrace" / "utils" / "__init__.py",
    PROJECT_ROOT / "playtrace" / "utils" / "clock.py",
    PROJECT_ROOT / "playtrace" / "utils" / "hashing.py",
    PROJECT_ROOT / "playtrace" / "utils" / "platform.py",
    PROJECT_ROOT / "playtrace" / "utils" / "text.py",

    PROJECT_ROOT / "tests" / "test_identity.py",
    PROJECT_ROOT / "tests" / "test_merge_sessions.py",
    PROJECT_ROOT / "tests" / "test_classification.py",
    PROJECT_ROOT / "tests" / "test_report_render.py",
]

def main() -> None:
    for directory in DIRECTORIES:
        directory.mkdir(parents=True, exist_ok=True)

    for file_path in FILES:
        file_path.touch(exist_ok=True)

    print(f"Created project structure under: {PROJECT_ROOT.resolve()}")

if __name__ == "__main__":
    main()