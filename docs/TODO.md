# TODO

This file tracks outstanding work only. Completed work is moved to [docs/CHANGELOG.md](/C:/Users/ryanf/github/_new/playtrace/docs/CHANGELOG.md).

## OPEN

### PR REVIEW REVISIONS

Skip to content

playtrace
Repository navigation
Code
Issues
Pull requests
1
 (1)
Agents
Actions
Projects
Security and quality
Insights
Settings
Important update
On April 24 we'll start using GitHub Copilot interaction data for AI model training unless you opt out. Review this update and manage your preferences in your GitHub account settings.

Implement incomplete modules and diagnostics cleanup

+2,683
-495
Lines changed: 2683 additions & 495 deletions
31 (31)
Commits1 (1)
Checks1 (1)
Files changed45 (45)
Open
Implement incomplete modules and diagnostics cleanup#2

Summary
implement the incomplete utils, normalize, config, and store modules defined by the active requirements/design/tasks spec bundle
integrate the new helpers into existing identity and database flows, add regression coverage and PE fixtures, and extract a shared inspection model
refresh diagnostics work by installing mypy, fixing live typing issues, and clearing docs/ERRORS.json after a clean type-check run
Test Plan
uv run pytest
uv run mypy playtrace
Summary by Sourcery
Complete the previously stubbed normalization, configuration, storage, and utility modules and wire them into identity, ingest, and database flows while keeping timestamp handling and inspection types consistent.

New Features:

Introduce PE executable metadata extraction, Windows path normalization, TOML-based configuration loading, and SHA-1 hashing and platform helper utilities.
Add typed repository layer and schema migration engine for SQLite-backed executables, sessions, titles, and user mappings, plus a shared inspection detail model used by services and rendering.
Bug Fixes:

Normalize parser and ingest timestamp handling, ensuring robust parsing of sample data and consistent timezone-aware storage via a shared clock utility.
Tighten parser contracts to operate on generic sequences of artifacts and harden prefetch parsing against malformed payloads.
Enhancements:

Refine the database connection management and datetime serialization/parsing to use a centralized clock abstraction and ensure connections are properly closed.
Align identity normalization with the new path normalizer while preserving compatibility for existing callers.
Update documentation to move the incomplete-modules and diagnostics work  TODO into the changelog.
Build:

Extend project dependencies with PE and Windows crypto libraries and define a dev dependency group including mypy, pytest, and Hypothesis for reproducible diagnostics.
Documentation:

Document completion of the incomplete-modules bundle and diagnostics cleanup in the changelog and TODO tracker.
Tests:

Add extensive unit and property-based tests for repositories, migrations, configuration loading, metadata extraction, hashing, clock, platform detection, path normalization, ingest registry, and shared inspection models to prevent regressions.
Summary by CodeRabbit
New Features

Added TOML-based configuration loading with validation and defaults.
Added path normalization utilities with environment variable expansion.
Added Windows executable metadata extraction (product info, signing details).
Added database migration and repository layers for persistent storage.
Added shared utilities for UTC time handling, file hashing, and platform detection.
Bug Fixes

Fixed defensive timestamp parsing in data collectors and parsers to handle missing or malformed timestamps gracefully.
Refactoring

Unified timestamp handling across the database layer using centralized UTC clock.
Moved inspection details model to shared layer.
Improved resource cleanup for database connections.
Documentation

Updated changelog and TODO tracking with completed implementation milestones.
Cleared diagnostic error log following type-checking cleanup.
Tests

Added comprehensive test coverage for config, migrations, repositories, pathing, platform detection, metadata extraction, and timestamp handling.
Chores

Updated dependencies: added Windows-specific libraries and dev testing tools.
Mention @copilot in a comment to make changes to this pull request.

Implement incomplete modules and diagnostics cleanup
1da7c09
 Copilot AI review requested due to automatic review settings
@sourcery-ai
sourcery-ai bot

Reviewer's Guide
Implements the previously stubbed normalize, config, store, and utils modules (metadata extraction, path normalization, config loading/validation, DB migrations, repositories, time/hashing/platform utilities), wires them into existing ingest/parse/identity/database flows, and adds tests/fixtures plus mypy/dev tooling so the type-check diagnostics snapshot is clean.

Class diagram for store Database, migrations, and repositories

Class diagram for normalize, config, utils, and inspection model

File-Level Changes
Change	Details	Files
Introduce typed generic repository and migration infrastructure for SQLite-backed store and update Database to use shared Clock-based timestamp handling.
Add generic Repository base class and concrete repositories for executables, sessions, titles, and user mappings with JSON and datetime serialization helpers.
Implement MappingRepository lookups that normalize targets via IdentityNormalizer and support candidate matching for raw Windows paths.
Add Migration and MigrationEngine with schema_version tracking, version application/validation, and transactional execscript execution.
Extend Database to use a managed sqlite3.Connection subclass, enforce foreign keys, and centralize timestamp formatting/parsing through Clock for all persisted entities including demo seed data and snapshots.
Add focused and property-based tests for repositories, migration sequencing/rollback, DB timestamp behavior, and repository use of Database.connect context management.
playtrace/store/repositories.py
playtrace/store/migrations.py
playtrace/store/db.py
tests/test_store_schema.py
tests/test_repositories.py
tests/test_migrations.py
Implement normalization and utility helpers for PE metadata extraction, Windows path normalization, clock/timezone handling, hashing, and platform detection, and integrate them into identity normalization and tests.
Add MetadataExtractor that uses pefile and Windows Crypto APIs (via pywin32) to read version resources and signer CN  PE files, with robust fallbacks and normalization.
Implement PathNormalizer to strip quotes, expand environment variables, normalize slashes, absolutize and lowercase Windows paths, and plug it into IdentityNormalizer._normalize_path with defensive try/except and backward-compatible fallback.
Introduce Clock utility to provide UTC-aware now(), ISO8601 parse/format with UTC normalization, and integrate it into Database and tests (including behavior for existing offset timestamps).
Add Hasher utility for SHA1 hashing of strings and files with chunked IO and safe error handling for missing/permission-denied files.
Add PlatformDetector/PlatformInfo to cache Windows environment details (version, system dir, Program Files, user profile) with non-Windows no-op behavior.
Add comprehensive tests for metadata extraction using PE fixtures, path normalization behaviors, clock semantics and round-trips, hashing correctness/idempotence, and platform detection/caching.
playtrace/normalize/metadata.py
playtrace/normalize/pathing.py
playtrace/utils/clock.py
playtrace/utils/hashing.py
playtrace/utils/platform.py
playtrace/normalize/identity.py
tests/test_identity.py
tests/test_metadata.py
tests/test_pathing.py
tests/test_clock.py
tests/test_hashing.py
tests/test_platform.py
Add configuration model and loader for TOML-based settings with validation and defaults, plus tests for behavior and round-trips.
Create Config_Model dataclass with fields for session merge window, default sources, and classification overrides, including type and value validation against SourceName enum.
Implement ConfigLoader to read an optional TOML file, handle missing/invalid files, normalize session/sources/classification sections, and apply defaults when sections/keys are absent.
Write property-based tests covering invalid values/types, valid TOML parsing, default application, round-tripping through TOML, handling of unknown fields, missing paths, and minimal configs.
playtrace/config/models.py
playtrace/config/loader.py
tests/test_config.py
Tighten ingest and parser contracts, add a shared inspection model, and align type hints with runtime behavior for mypy cleanliness and inspector/render integration.
Change parser interfaces to accept Sequence[RawArtifact] instead of list, and update tests to assert the type hints use Sequence[RawArtifact].
Harden ingest collectors (security_log, srum, userassist, prefetch) and the PrefetchParser to defensively handle missing/null timestamp fields and non-list last_run_times, casting values through str before isoformat.
Extract InspectionDetail dataclass into playtrace.models.inspection and update InspectorService and render.source_views to share this type, with a test asserting the shared type hints.
Add tests that build parsers  the ingest registry, verify they satisfy the protocol and produce records  sample artifacts, and assert sample collector observed_at timestamps are timezone-aware and as expected.
playtrace/parsers/prefetch.py
playtrace/parsers/amcache.py
playtrace/parsers/bam.py
playtrace/parsers/security_log.py
playtrace/parsers/srum.py
playtrace/parsers/userassist.py
playtrace/ingest/security_log.py
playtrace/ingest/srum.py
playtrace/ingest/userassist.py
playtrace/ingest/prefetch.py
playtrace/ingest/registry.py
playtrace/models/inspection.py
playtrace/services/inspector.py
playtrace/render/source_views.py
tests/test_ingest_registry.py
tests/test_inspection_model.py
Update project metadata, docs, and dev tooling to reflect completed modules and mypy-based diagnostics workflow.
Add pefile and pywin32 runtime dependencies and introduce a dev dependency group with hypothesis, mypy, and pytest in pyproject.toml.
Mark previously incomplete modules as finished in docs/TODO.md and describe the new functionality and diagnostics cleanup in docs/CHANGELOG.md.
Refresh docs/ERRORS.json (now empty/ignored) and update .gitignore/uv.lock to align with the new dependency set and tooling expectations.
pyproject.toml
docs/TODO.md
docs/CHANGELOG.md
.gitignore
docs/ERRORS.json
uv.lock
Tips and commands
@coderabbitai
coderabbitai bot

ℹ️ Recent review info
Walkthrough
This pull request implements a configuration system (TOML-based), Windows executable metadata extraction, path normalization utilities, a SQLite schema migration framework with a repository pattern, UTC-aware clock helpers, and updates related components including ingest collectors, parsers, and the database layer. Documentation and comprehensive test coverage are included.

Changes
Cohort / File(s)	Summary
Configuration System
playtrace/config/loader.py, playtrace/config/models.py, tests/test_config.py	Added ConfigLoader class with load(path) entry point for TOML parsing and Config_Model dataclass with validation for merge window, default sources, and classification overrides. Includes comprehensive test suite validating parsing, defaults, and round-trip consistency.
Executable Metadata Extraction
playtrace/normalize/metadata.py, tests/test_metadata.py	Introduced MetadataExtractor and ExecutableMetadata for Windows binary version-info and certificate extraction via pefile and win32crypt. Includes tests covering PE fixture parsing and idempotency.
Path Normalization
playtrace/normalize/pathing.py, tests/test_pathing.py	Added PathNormalizer.normalize() for Windows path resolution (environment variable expansion, quote stripping, forward-slash conversion, absolute path conversion). Property-based and deterministic tests validate behavior across edge cases.
Identity Normalization
playtrace/normalize/identity.py, tests/test_identity.py	Updated IdentityNormalizer to inject and delegate to PathNormalizer with fallback to prior behavior. New test verifies environment variable expansion through the injected normalizer.
Ingest & Parser Updates
playtrace/ingest/prefetch.py, playtrace/ingest/security_log.py, playtrace/ingest/srum.py, playtrace/ingest/userassist.py, playtrace/parsers/amcache.py, playtrace/parsers/bam.py, playtrace/parsers/prefetch.py, playtrace/parsers/security_log.py, playtrace/parsers/srum.py, playtrace/parsers/userassist.py, tests/test_ingest_registry.py	Ingest collectors now safely derive observed_at  optional timestamp fields via .get() with None fallback. All parser parse() methods broadened to accept Sequence[RawArtifact] instead of list[RawArtifact]. Ingest registry tests validate parser contracts and timestamp correctness.
Utility Modules
playtrace/utils/clock.py, playtrace/utils/hashing.py, playtrace/utils/platform.py, tests/test_clock.py, tests/test_hashing.py, tests/test_platform.py	Added Clock (UTC time and ISO-8601 formatting), Hasher (SHA-1 string/file hashing), and PlatformDetector (Windows environment detection) utilities. Each includes comprehensive property-based and deterministic tests.
Database & Store Layer
playtrace/store/db.py, playtrace/store/migrations.py, playtrace/store/repositories.py, tests/test_migrations.py, tests/test_repositories.py, tests/test_store_schema.py	Added lightweight SQLite migration engine (MigrationEngine, Migration) for schema versioning, generic Repository[T] abstraction with CRUD + specialized query methods, concrete repositories for ExecutableIdentity, SessionRecord, TitleAggregate, UserMapping, and updated Database to use Clock for consistent timestamp handling. Tests validate migration linearization, rollback, CRUD operations, normalization, and clock integration.
Model Refactoring
playtrace/models/inspection.py, playtrace/services/inspector.py, playtrace/render/source_views.py, tests/test_inspection_model.py	Extracted InspectionDetail dataclass  InspectorService into shared playtrace.models.inspection module. render_inspection and related layers now import  the centralized location. Test validates type consistency across layers.
Project Configuration & Documentation
.gitignore, pyproject.toml, docs/CHANGELOG.md, docs/ERRORS.json, docs/TODO.md	Added .hypothesis/ to .gitignore. Expanded pyproject.toml with pefile, pywin32 runtime dependencies and dev group (hypothesis, mypy, pytest). Updated CHANGELOG.md with feature completions and fixes. Cleared ERRORS.json (mypy diagnostics) and TODO.md (open tasks moved to CHANGELOG).
Sequence Diagram(s)

Estimated code review effort
🎯 4 (Complex) | ⏱️ ~75 minutes

Poem
🐰 Hops of joy through config files,
Paths normalized across all trials,
Migrations smooth, repos so neat,
Clock precision, metadata sweet!
 Windows binaries to TOML's grace,
PlayTrace now runs at SQLite's pace! ⏰✨

Note

🎁 Summarized by CodeRabbit Free
Comment @coderabbitai help to get the list of available commands and usage tips.

Copilot started reviewing on behalf of  20 minutes ago
@qodo-code-review
qodo-code-review bot

20 minutes ago
Review Summary by Qodo
Implement incomplete modules and diagnostics cleanup

✨ Enhancement 🧪 Tests 📝 Documentation

Grey Divider

Walkthroughs
Description

 Implements incomplete core modules (utils, normalize, config, store) with comprehensive
  functionality:
- **Clock utility** for consistent timezone-aware datetime operations with ISO8601 serialization
- **PathNormalizer** for Windows path normalization with environment variable expansion
- **PlatformDetector** for platform detection and system path resolution with caching
- **Hasher** utility for SHA1 hashing of strings and files
- **MetadataExtractor** for PE file metadata and digital signature extraction
- **Config_Model and ConfigLoader** for TOML configuration parsing with validation
- **Repository pattern** with generic base class and concrete implementations for database
  persistence (ExecutableIdentity, SessionRecord, TitleAggregate, UserMapping)
- **MigrationEngine** for database schema versioning with transaction support
 Integrates new utilities into existing flows:
- IdentityNormalizer now uses PathNormalizer for path canonicalization
- Database uses Clock for consistent datetime handling across all operations
- All parsers updated to accept Sequence[RawArtifact] for protocol compliance
- Defensive timestamp parsing added to collectors for type inconsistency handling
 Extracts InspectionDetail to shared models module to eliminate circular dependencies
 Adds comprehensive regression and property-based test coverage using Hypothesis for all new
  modules
 Installs mypy for type checking and clears all 23 previous diagnostics after fixing typing
  issues
 Updates documentation with completed work tracking and changelog entries
 Adds production dependencies (pefile, pywin32) and dev tools (hypothesis, mypy, pytest)
Diagram
Grey Divider

File Changes
1. playtrace/store/repositories.py ✨ Enhancement  +367/-0

Implement repository pattern for database persistence layer

 Implements generic Repository base class with CRUD operations for database entities
 Adds concrete repository implementations for ExecutableIdentity, SessionRecord,
 TitleAggregate, and UserMapping models
 Provides entity-to-record serialization and row-to-entity deserialization with proper type
 conversions
 Includes specialized query methods like find_by_normalized_key, find_by_exe_id,
 find_by_classification, and find_by_target
playtrace/store/repositories.py

1. tests/test_repositories.py 🧪 Tests  +406/-0
2. playtrace/store/db.py ✨ Enhancement  +46/-24
View more (37)
Grey Divider

Qodo Logo

@qodo-code-review
qodo-code-review bot

20 minutes ago

Code Review by Qodo
🐞 Bugs (3)   📘 Rule violations (1)   📎 Requirement gaps (0)
Grey Divider

Action required

1. Config_Model class misnamed 📘 ⚙
2. Hardcoded cwd test path 🐞 ☼
3. MappingRepository enum parsing crash 🐞 ≡

Remediation recommended

1. Repository timestamps not UTC 🐞 ⚙
Grey Divider

ⓘ The new review experience is currently in Beta. Learn more
Grey Divider

Qodo Logo

sourcery-ai[bot]
sourcery-ai bot reviewed 19 minutes ago
sourcery-ai bot
left a comment
Hey - I've found 4 security issues, 3 other issues, and left some high level feedback:

Security issues:

Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option. (link)
Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option. (link)
Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option. (link)
Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option. (link)
General comments:

Several new tests (e.g. in test_pathing.py, test_platform.py, and Windows-style chdir/paths) assume a Windows filesystem and environment; consider guarding these with platform checks or using PureWindowsPath-only logic so the test suite res runnable on non-Windows hosts.
The MigrationEngine._apply_migration method builds a multi-statement SQL script with string interpolation for values like applied_at and description; to avoid subtle quoting/escaping issues over time, consider switching the INSERT INTO schema_version step to a parameterized statement executed separately  the DDL script.
Prompt for AI Agents
Help me be more useful! Please click 👍 or 👎 on each comment and I'll use the feedback to improve your reviews.
playtrace/store/migrations.py
Comment on lines +97 to +98
    def _timestamp(self) -> str:
        return Clock.format_iso8601(Clock.utc_now()) or Clock.utc_now().isoformat()
@sourcery-ai
sourcery-ai bot
19 minutes ago
suggestion: Avoid calling Clock.utc_now() twice in_timestamp to prevent tiny inconsistencies and unnecessary work.

The method calls Clock.utc_now() twice, which can produce slightly different values and does extra work. Capture it once and reuse it:

    def _timestamp(self) -> str:
        now = Clock.utc_now()
        return Clock.format_iso8601(now) or now.isoformat()
Suggested change
    def _timestamp(self) -> str:
        return Clock.format_iso8601(Clock.utc_now()) or Clock.utc_now().isoformat()
    def _timestamp(self) -> str:
        now = Clock.utc_now()
        return Clock.format_iso8601(now) or now.isoformat()
	Reply...
tests/test_metadata.py
Comment on lines +59 to +62
def test_metadata_extractor_reads_signed_pe_with_version_info() -> None:
    metadata = MetadataExtractor().extract(FIXTURES / "signed_with_version.exe")

    assert metadata == ExecutableMetadata(
@sourcery-ai
sourcery-ai bot
19 minutes ago
issue (testing): Metadata tests assume Windows signature APIs are available and will fail on non-Windows platforms or when win32crypt is not installed.

MetadataExtractor._extract_signature only returns a signer when running on Windows with win32crypt available. On other platforms or without pywin32, signer is always None, so these tests will fail because they assert a non-None signer. Please either mark these tests as Windows-only (e.g. @pytest.mark.skipif(platform.system() != "Windows", ...)) or conditionalize the assertions based on PlatformDetector.detect().windows_version and/or win32crypt availability.

	Reply...
tests/test_pathing.py
Comment on lines +44 to +49
def test_path_normalizer_resolves_relative_paths_to_absolute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(r"C:\Users\ryanf")

    assert PathNormalizer().normalize(r"Games\Balatro.exe") == r"c:\users\ryanf\games\balatro.exe"
@sourcery-ai
sourcery-ai bot
19 minutes ago
issue (testing): Path normalizer test relies on a specific Windows directory that may not exist on CI or non-Windows systems.

Using monkeypatch.chdir(r"C:\Users\ryanf") will break on non-Windows environments or Windows agents with a different username. To keep the behavior under test (relative → absolute resolution) but make the test portable, use a temporary directory fixture, e.g. monkeypatch.chdir(tmp_path) and assert that PathNormalizer().normalize("Games/ Balatro.exe") resolves to the corresponding absolute path under tmp_path (with the expected normalization to lowercase and backslashes).

	Reply...
playtrace/store/repositories.py
Comment on lines +28 to +31
            row = conn.execute(
                f"SELECT *  {self.table_name} WHERE {self.id_column} = ?",
                (entity_id,),
            ).fetchone()
@sourcery-ai
sourcery-ai bot
19 minutes ago
security (python.sqlalchemy.security.sqlalchemy-execute-raw-query): Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option.

Source: opengrep

	Reply...
playtrace/store/repositories.py
Comment on lines +40 to +42
            rows = conn.execute(
                f"SELECT *  {self.table_name} ORDER BY {self.id_column} ASC"
            ).fetchall()
@sourcery-ai
sourcery-ai bot
19 minutes ago
security (python.sqlalchemy.security.sqlalchemy-execute-raw-query): Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option.

Source: opengrep

	Reply...
playtrace/store/repositories.py
Comment on lines +55 to +63
            conn.execute(
                f"""
                INSERT INTO {self.table_name} ({", ".join(columns)})
                VALUES ({placeholders})
                ON CONFLICT({self.id_column}) DO UPDATE SET
                    {assignments}
                """,
                tuple(record[column] for column in columns),
            )
@sourcery-ai
sourcery-ai bot
19 minutes ago
security (python.sqlalchemy.security.sqlalchemy-execute-raw-query): Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option.

Source: opengrep

	Reply...
playtrace/store/repositories.py
Comment on lines +74 to +77
            conn.execute(
                f"DELETE  {self.table_name} WHERE {self.id_column} = ?",
                (entity_id,),
            )
@sourcery-ai
sourcery-ai bot
19 minutes ago
security (python.sqlalchemy.security.sqlalchemy-execute-raw-query): Avoiding SQL string concatenation: untrusted input concatenated with raw SQL query can result in SQL Injection. In order to execute raw query safely, prepared statement should be used. SQLAlchemy provides TextualSQL to easily used prepared statement with named parameters. For complex SQL composition, use SQL Expression Language or Schema Definition Language. In most cases, SQLAlchemy ORM will be a better option.

Source: opengrep

	Reply...
@augmentcode
augmentcode bot

17 minutes ago
🤖 Augment PR Summary

Summary: This PR completes several previously-stubbed modules and refreshes diagnostics/type-checking so the codebase and tests align with the current requirements bundle.

Changes:

Added TOML-driven configuration support via playtrace/config (loader + validated config model).
Introduced normalization helpers for Windows paths and PE metadata extraction (version info + signer best-effort).
Added shared utility helpers for UTC clock handling, SHA1 hashing, and platform detection.
Refactored identity normalization to delegate path canonicalization to the new PathNormalizer with fallback behavior.
Expanded store layer with a migration engine and typed repository abstractions, plus improved DB connection lifecycle management.
Updated DB timestamp formatting/parsing to route through Clock for consistent UTC storage (including legacy offset parsing).
Adjusted parser signatures to accept Sequence[RawArtifact] and hardened sample ingest timestamp parsing.
Extracted a shared InspectionDetail model for service/render type consistency.
Added PE fixtures and broad regression/property-based test coverage for the new modules.
Added dev dependency group (Hypothesis/mypy/pytest) and cleared docs/ERRORS.json after a clean mypy run.
Technical Notes: New test suites exercise UTC normalization, TOML parsing defaults, repository round-trips, migration ordering/rollback behavior, and PE metadata extraction idempotence.

🤖 Was this summary useful? React with 👍 or 👎

augmentcode[bot]
augmentcode bot reviewed 17 minutes ago
augmentcode bot
left a comment
Review completed. 3 suggestions posted.

Fix All in Augment

Comment augment review to trigger a new review at any time.

playtrace/store/repositories.py
        return candidates

def _parse_datetime(value: str | None) -> datetime | None:
@augmentcode
augmentcode bot
17 minutes ago

_parse_datetime/_serialize_datetime use datetime.isoformat()/.isoformat() directly, so repository reads/writes can preserve non-UTC offsets and diverge  the Clock-normalized UTC behavior used in playtrace/store/db.py. This can lead to mixed timezone representations in persisted data and inconsistent datetime.tzinfo in loaded models.

Severity: medium

Other Locations
playtrace/store/repositories.py:340
playtrace/store/repositories.py:362
Fix This in Augment

🤖 Was this useful? React with 👍 or 👎, or 🚀 if it prevented an incident/outage.

	Reply...
pyproject.toml
    "rich>=13.7",
    "pydantic>=2.7",
    "pefile>=2024.8.26",
    "pywin32>=311",
@augmentcode
augmentcode bot
17 minutes ago

Adding pywin32 as an unconditional runtime dependency will make installs fail on non-Windows platforms (even though runtime code paths often guard Windows-only behavior). If non-Windows development/test execution is expected, this dependency placement can be a hard blocker.

Severity: medium

Fix This in Augment

🤖 Was this useful? React with 👍 or 👎, or 🚀 if it prevented an incident/outage.

	Reply...
playtrace/normalize/metadata.py

class MetadataExtractor:
    _EMPTY = ExecutableMetadata(
@augmentcode
augmentcode bot
17 minutes ago

MetadataExtractor._EMPTY is a single shared mutable ExecutableMetadata instance; if any caller mutates the returned object, later calls can observe that mutated state. Returning a fresh value object per call avoids cross-call state leakage.

Severity: low

Fix This in Augment

🤖 Was this useful? React with 👍 or 👎, or 🚀 if it prevented an incident/outage.

	Reply...
qodo-code-review[bot]
qodo-code-review bot reviewed 14 minutes ago
playtrace/config/models.py
Comment on lines +8 to +12
@dataclass(slots=True)
class Config_Model:
    session_merge_dedupe_window_minutes: int = 2
    default_sources: list[str] = field(default_factory=list)
    classification_overrides: dict[str, str] = field(default_factory=dict)
@qodo-code-review
qodo-code-review bot
14 minutes ago
Action required

1. config_model class misnamed 📘 Rule violation ⚙ tainability

The new config dataclass is named Config_Model, which violates the project’s PascalCase naming
convention for classes. This introduces inconsistent public API naming across modules and tests.
Agent Prompt
	Reply...
tests/test_pathing.py
Comment on lines +44 to +50
def test_path_normalizer_resolves_relative_paths_to_absolute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(r"C:\Users\ryanf")

    assert PathNormalizer().normalize(r"Games\Balatro.exe") == r"c:\users\ryanf\games\balatro.exe"

@qodo-code-review
qodo-code-review bot
14 minutes ago
Action required

1. Hardcoded cwd test path 🐞 Bug ☼ Reliability

tests/test_pathing.py changes CWD to a hardcoded directory (C:\Users\ryanf) that likely doesn't
exist on CI or other machines, causing FileNotFoundError before assertions run. This makes the test
suite non-deterministic and can block merges unrelated to path normalization logic.
Agent Prompt
	Reply...
playtrace/store/repositories.py
Comment on lines +331 to +343
    def_row_to_entity(self, conn: sqlite3.Connection, row: sqlite3.Row) -> UserMapping:
        target = row["target"]
        return UserMapping(
            mapping_id=row["mapping_id"],
            target=target,
            title=row["title"],
            classification=Classification(row["classification"]) if row["classification"] else None,
            launcher=row["launcher"],
            ignore=bool(row["ignore"]),
            created_at=datetime.isoformat(row["created_at"]),
            normalized_key=self._normalizer.normalize_executable_target(target),
            confidence=ConfidenceLevel(row["confidence"]),
        )
@qodo-code-review
qodo-code-review bot
14 minutes ago
Action required

1. Mappingrepository enum parsing crash 🐞 Bug ≡ Correctness

MappingRepository._row_to_entity constructs Classification/ConfidenceLevel directly  persisted
strings, so any invalid historical values will raise ValueError and crash loads. This contradicts
Database.load_user_mappings(), which explicitly tolerates invalid classifications and defaults
confidence, and is already relied upon by tests.
Agent Prompt
	Reply...
Copilot AI reviewed 14 minutes ago
Copilot AI
left a comment
Pull request overview
Implements the previously incomplete utils, normalize, config, and store modules; integrates them into identity/database flows; adds extensive regression/property tests and PE fixtures; and refreshes type-checking diagnostics by adding mypy plus cleaning docs/ERRORS.json.

Changes:

Added core helper modules (clock, hashing, platform), normalization utilities (path + PE metadata), and config loading/validation.
Introduced repository + migration layers for the SQLite store and integrated shared InspectionDetail model across service/render code.
Added mypy/Hypothesis dev tooling, updated dependencies/lockfile, and added broad test coverage + fixtures.
Reviewed changes
Copilot reviewed 40 out of 45 changed files in this pull request and generated 7 comments.

Show a summary per file
💡 Add Copilot custom instructions for smarter, more guided reviews. Learn how to get started.

playtrace/config/models.py

@dataclass(slots=True)
class Config_Model:
Copilot AI
14 minutes ago
The class name Config_Model is inconsistent with the project’s other dataclass model names (e.g., UserMapping in playtrace/models/mapping.py:10, SessionRecord in playtrace/models/session.py:9). Consider renaming to ConfigModel (and updating imports) to keep public API naming consistent and avoid underscore-separated class names.

Suggested change
class Config_Model:
class ConfigModel:
Copilot uses AI. Check for mistakes.
	Reply...
docs/TODO.md
Comment on lines 11 to +13
- PR #1 review corrections were verified as complete and moved to [docs/CHANGELOG.md](/C:/Users/ryanf/github/_new/playtrace/docs/CHANGELOG.md).
- Incomplete modules implementation  [docs/requirements.md](/C:/Users/ryanf/github/_new/playtrace/docs/requirements.md), [docs/design.md](/C:/Users/ryanf/github/_new/playtrace/docs/design.md), and [docs/tasks.md](/C:/Users/ryanf/github/_new/playtrace/docs/tasks.md) was completed and moved to [docs/CHANGELOG.md](/C:/Users/ryanf/github/_new/playtrace/docs/CHANGELOG.md).
- Diagnostics cleanup for [docs/ERRORS.json](/C:/Users/ryanf/github/_new/playtrace/docs/ERRORS.json) was completed after refreshing the snapshot  a clean `mypy` run.
Copilot AI
14 minutes ago
These links use absolute local filesystem paths (e.g., /C:/Users/...) which won’t resolve for other contributors or when rendered on GitHub. Switch them to repository-relative links (e.g., docs/CHANGELOG.md, docs/requirements.md, docs/design.md, docs/tasks.md, docs/ERRORS.json).

Copilot uses AI. Check for mistakes.
	Reply...
pyproject.toml
    "rich>=13.7",
    "pydantic>=2.7",
    "pefile>=2024.8.26",
    "pywin32>=311",
Copilot AI
14 minutes ago
pywin32 is added as an unconditional runtime dependency, but it only supports Windows and will break installs on non-Windows environments. Consider using a PEP 508 environment marker (e.g., pywin32>=311; platform_system == 'Windows') or moving it behind an extra/dependency group so non-Windows users can still install and run non-Windows-safe parts (type checks, docs, etc.).

Suggested change
    "pywin32>=311",
    "pywin32>=311; platform_system == 'Windows'",
Copilot uses AI. Check for mistakes.
	Reply...
playtrace/utils/platform.py
Comment on lines +35 to +37
        system_root = cls._clean(os.environ.get("SystemRoot") or os.environ.get("WINDIR"))
        system_directory = str(Path(system_root) / "System32") if system_root else None

Copilot AI
14 minutes ago
system_directory is built with pathlib.Path, which uses the host OS path flavor; if this code is exercised on non-Windows (including tests that monkeypatch platform.system()), it can produce mixed separators like C:\Windows/System32. Since these are Windows paths, use PureWindowsPath (or manual joining) to ensure consistent \ separators regardless of host OS.

Copilot uses AI. Check for mistakes.
	Reply...
tests/test_pathing.py
Comment on lines +44 to +50
def test_path_normalizer_resolves_relative_paths_to_absolute(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(r"C:\Users\ryanf")

    assert PathNormalizer().normalize(r"Games\Balatro.exe") == r"c:\users\ryanf\games\balatro.exe"

Copilot AI
14 minutes ago
This test changes the working directory to a hard-coded path (C:\Users\ryanf) that may not exist on the test runner, making the suite flaky/failing. Use tmp_path (create a directory and monkeypatch.chdir(tmp_path)) and assert against the normalized absolute path derived  that temporary directory instead.

Copilot uses AI. Check for mistakes.
	Reply...
playtrace/store/repositories.py
Comment on lines +338 to +342
            launcher=row["launcher"],
            ignore=bool(row["ignore"]),
            created_at=datetime.isoformat(row["created_at"]),
            normalized_key=self._normalizer.normalize_executable_target(target),
            confidence=ConfidenceLevel(row["confidence"]),
Copilot AI
14 minutes ago
MappingRepository._row_to_entity parses created_at with datetime.isoformat but does not normalize to UTC or handle naive timestamps the same way Database does via Clock.parse_iso8601. This can yield inconsistent created_at values (e.g., offset-aware -08:00 vs UTC) depending on stored data; consider using the shared Clock helpers here too.

Copilot uses AI. Check for mistakes.
	Reply...
playtrace/store/repositories.py
Comment on lines +356 to +363
def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.isoformat(value)

def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None
Copilot AI
14 minutes ago
The repository-level _parse_datetime/_serialize_datetime helpers use raw datetime.isoformat() / datetime.isoformat(), which can persist/return naive timestamps (no +00:00) and won’t normalize offset-aware timestamps to UTC. To keep timestamp behavior consistent with Database/MigrationEngine (which use Clock), consider delegating to Clock.parse_iso8601 / Clock.format_iso8601 here.

Copilot uses AI. Check for mistakes.
	Reply...
chatgpt-codex-connector[bot]
chatgpt-codex-connector bot reviewed 13 minutes ago
chatgpt-codex-connector bot
left a comment
💡 Codex Review
Here are some automated review suggestions for this pull request.

Reviewed commit: 1da7c091c0

ℹ️ About Codex in GitHub

Your team has set up Codex to review pull requests in this repo. Reviews are triggered when you

Open a pull request for review
Mark a draft as ready
Comment "@codex review".
If Codex has suggestions, it will comment; otherwise it will react with 👍.

Codex can also answer questions or update the PR. Try commenting "@codex address that feedback".

pyproject.toml
    "rich>=13.7",
    "pydantic>=2.7",
    "pefile>=2024.8.26",
    "pywin32>=311",
@chatgpt-codex-connector
chatgpt-codex-connector bot
13 minutes ago
P1 Badge Gate pywin32 dependency behind a Windows marker

Adding pywin32 as an unconditional runtime dependency makes environment resolution fail on non-Windows platforms before the app can start, even though the runtime code already treats win32crypt as optional. In practice this blocks uv run/uv build on Linux and macOS because pywin32 does not publish compatible distributions there; the dependency should be guarded with a platform marker (for example, sys_platform == 'win32') so non-Windows installs can still run the non-signature code paths.

Useful? React with 👍 / 👎.

	Reply...
playtrace/normalize/pathing.py
Comment on lines +31 to +34
        return os.path.expandvars(path)

    def _to_absolute(self, path: str) -> str:
        return path if PureWindowsPath(path).is_absolute() else os.path.abspath(path)
@chatgpt-codex-connector
chatgpt-codex-connector bot
13 minutes ago
P2 Badge Normalize Windows paths without host-OS path semantics

Using os.path.expandvars and os.path.abspath here makes normalization depend on the host OS instead of Windows rules: on non-Windows hosts, %ProgramFiles% is not expanded and relative Windows paths are prefixed with the POSIX working directory (e.g. \workspace\...), which then feeds into identity keys and mapping lookups. This causes incorrect canonical paths and deduping when processing Windows artifacts off-host; use Windows-path-aware logic (ntpath/PureWindowsPath-based expansion and absolute resolution) to keep normalization stable across platforms.

Useful? React with 👍 / 👎.

	Reply...
Merge info
Some checks were not successful
1 failing, 1 successful checks

failing checks
Sourcery review
Sourcery reviewFailing after 1m — ❌ Found 4 blocking security issues
successful checks
CodeRabbit
CodeRabbit — Review completed
No conflicts with base branch
Merging can be performed automatically.

You can also merge this with the command line.
Still in progress?

Add a comment
Comment

Add your comment here...
Remember, contributions to this repository should follow our GitHub Community Guidelines.
 ProTip! Add .patch or .diff to the end of URLs for Git’s plaintext views.
Reviewers
@sourcery-ai
sourcery-ai[bot]
@qodo-code-review
qodo-code-review[bot]
Copilot code review
Copilot
@chatgpt-codex-connector
chatgpt-codex-connector[bot]
+1 more reviewer
@augmentcode
augmentcode[bot]

Still in progress?
Assignees
No one—
Labels
None yet
Projects
None yet
Milestone
No milestone
Development
Successfully merging this pull request may close these issues.

None yet

Notifications
Customize
You’re receiving notifications because you authored the thread.
2 participants

Footer
© 2026 GitHub, Inc.
Footer navigation
Terms
Privacy
Security
Status
Community
Docs
Contact
Manage cookies
Do not share my personal information
