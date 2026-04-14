from pathlib import Path
import textwrap

PROJECT_ROOT = Path("playtrace")

FILES = {
    # Top-level files
    PROJECT_ROOT / "pyproject.toml": textwrap.dedent("""\
        [build-system]
        requires = ["setuptools>=68", "wheel"]
        build-backend = "setuptools.build_meta"

        [project]
        name = "playtrace"
        version = "0.1.0"
        description = "Graphing and reporting play/session artifacts"
        readme = "README.md"
        requires-python = ">=3.11"
        authors = [
          { name = "Your Name" }
        ]
        dependencies = []

        [project.scripts]
        playtrace = "playtrace.__main__:main"

        [tool.setuptools]
        include-package-data = true

        [tool.setuptools.packages.find]
        where = ["."]
        include = ["playtrace*"]
    """),

    PROJECT_ROOT / "README.md": textwrap.dedent("""\
        # playtrace

        A Python project for ingesting, normalizing, classifying, merging, and reporting play/session artifacts.

        ## Development

        Create the project structure with the bootstrap script, then install in editable mode:

        ```bash
        pip install -e .
        ```

        Run tests with:

        ```bash
        pytest
        ```
    """),

    PROJECT_ROOT / ".gitignore": textwrap.dedent("""\
        __pycache__/
        *.py[cod]
        *.pyo
        *.pyd
        *.so
        .Python
        .pytest_cache/
        .mypy_cache/
        .ruff_cache/
        .coverage
        htmlcov/
        .venv/
        venv/
        env/
        ENV/
        build/
        dist/
        *.egg-info/
        .DS_Store
        .idea/
        .vscode/
    """),

    # Package root
    PROJECT_ROOT / "playtrace" / "__init__.py": textwrap.dedent("""\
        from .version import __version__

        __all__ = ["__version__"]
    """),

    PROJECT_ROOT / "playtrace" / "__main__.py": textwrap.dedent("""\
        def main() -> None:
            print("playtrace CLI not implemented yet")


        if __name__ == "__main__":
            main()
    """),

    PROJECT_ROOT / "playtrace" / "version.py": '__version__ = "0.1.0"\n',

    # cli
    PROJECT_ROOT / "playtrace" / "cli" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "app.py": textwrap.dedent("""\
        def build_app() -> None:
            \"\"\"Build and configure the CLI application.\"\"\"
            raise NotImplementedError
    """),
    PROJECT_ROOT / "playtrace" / "cli" / "common.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_scan.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_report.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_titles.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_sessions.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_inspect.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_map.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_doctor.py": "",
    PROJECT_ROOT / "playtrace" / "cli" / "cmd_export.py": "",

    # config
    PROJECT_ROOT / "playtrace" / "config" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "config" / "loader.py": "",
    PROJECT_ROOT / "playtrace" / "config" / "models.py": "",

    # models
    PROJECT_ROOT / "playtrace" / "models" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "models" / "enums.py": "",
    PROJECT_ROOT / "playtrace" / "models" / "artifacts.py": "",
    PROJECT_ROOT / "playtrace" / "models" / "executable.py": "",
    PROJECT_ROOT / "playtrace" / "models" / "session.py": "",
    PROJECT_ROOT / "playtrace" / "models" / "title.py": "",
    PROJECT_ROOT / "playtrace" / "models" / "mapping.py": "",
    PROJECT_ROOT / "playtrace" / "models" / "report.py": "",

    # parsers
    PROJECT_ROOT / "playtrace" / "parsers" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "parsers" / "base.py": "",
    PROJECT_ROOT / "playtrace" / "parsers" / "security_log.py": "",
    PROJECT_ROOT / "playtrace" / "parsers" / "prefetch.py": "",
    PROJECT_ROOT / "playtrace" / "parsers" / "userassist.py": "",
    PROJECT_ROOT / "playtrace" / "parsers" / "srum.py": "",
    PROJECT_ROOT / "playtrace" / "parsers" / "amcache.py": "",
    PROJECT_ROOT / "playtrace" / "parsers" / "bam.py": "",

    # ingest
    PROJECT_ROOT / "playtrace" / "ingest" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "ingest" / "orchestrator.py": "",
    PROJECT_ROOT / "playtrace" / "ingest" / "registry.py": "",

    # normalize
    PROJECT_ROOT / "playtrace" / "normalize" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "normalize" / "identity.py": "",
    PROJECT_ROOT / "playtrace" / "normalize" / "pathing.py": "",
    PROJECT_ROOT / "playtrace" / "normalize" / "metadata.py": "",

    # classify
    PROJECT_ROOT / "playtrace" / "classify" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "classify" / "rules.py": "",
    PROJECT_ROOT / "playtrace" / "classify" / "heuristics.py": "",
    PROJECT_ROOT / "playtrace" / "classify" / "resolver.py": "",

    # merge
    PROJECT_ROOT / "playtrace" / "merge" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "merge" / "events.py": "",
    PROJECT_ROOT / "playtrace" / "merge" / "sessions.py": "",
    PROJECT_ROOT / "playtrace" / "merge" / "titles.py": "",
    PROJECT_ROOT / "playtrace" / "merge" / "confidence.py": "",

    # store
    PROJECT_ROOT / "playtrace" / "store" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "store" / "db.py": "",
    PROJECT_ROOT / "playtrace" / "store" / "schema.py": "",
    PROJECT_ROOT / "playtrace" / "store" / "repositories.py": "",
    PROJECT_ROOT / "playtrace" / "store" / "migrations.py": "",

    # render
    PROJECT_ROOT / "playtrace" / "render" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "render" / "console.py": "",
    PROJECT_ROOT / "playtrace" / "render" / "theme.py": "",
    PROJECT_ROOT / "playtrace" / "render" / "tables.py": "",
    PROJECT_ROOT / "playtrace" / "render" / "cards.py": "",
    PROJECT_ROOT / "playtrace" / "render" / "badges.py": "",
    PROJECT_ROOT / "playtrace" / "render" / "timeline.py": "",
    PROJECT_ROOT / "playtrace" / "render" / "report_views.py": "",

    # services
    PROJECT_ROOT / "playtrace" / "services" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "services" / "scanner.py": "",
    PROJECT_ROOT / "playtrace" / "services" / "reporter.py": "",
    PROJECT_ROOT / "playtrace" / "services" / "mapper.py": "",
    PROJECT_ROOT / "playtrace" / "services" / "inspector.py": "",
    PROJECT_ROOT / "playtrace" / "services" / "doctor.py": "",
    PROJECT_ROOT / "playtrace" / "services" / "exporter.py": "",

    # utils
    PROJECT_ROOT / "playtrace" / "utils" / "__init__.py": "",
    PROJECT_ROOT / "playtrace" / "utils" / "clock.py": "",
    PROJECT_ROOT / "playtrace" / "utils" / "hashing.py": "",
    PROJECT_ROOT / "playtrace" / "utils" / "platform.py": "",
    PROJECT_ROOT / "playtrace" / "utils" / "text.py": "",

    # tests
    PROJECT_ROOT / "tests" / "test_identity.py": textwrap.dedent("""\
        def test_placeholder() -> None:
            assert True
    """),
    PROJECT_ROOT / "tests" / "test_merge_sessions.py": "",
    PROJECT_ROOT / "tests" / "test_classification.py": "",
    PROJECT_ROOT / "tests" / "test_report_render.py": "",
}

DIRECTORIES = {
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
}


def write_file(path: Path, content: str, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        return

    path.write_text(content, encoding="utf-8")


def main() -> None:
    for directory in sorted(DIRECTORIES):
        directory.mkdir(parents=True, exist_ok=True)

    for path, content in FILES.items():
        write_file(path, content, overwrite=False)

    print(f"Created project structure at: {PROJECT_ROOT.resolve()}")
    print("Existing files were left untouched.")


if __name__ == "__main__":
    main()