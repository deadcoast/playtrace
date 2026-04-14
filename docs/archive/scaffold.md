# playtrace Python Scaffold

## Repository layout

```text
playtrace/
├── pyproject.toml
├── README.md
├── .gitignore
├── playtrace/
│   ├── __init__.py
│   ├── __main__.py
│   ├── version.py
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── common.py
│   │   ├── cmd_scan.py
│   │   ├── cmd_report.py
│   │   ├── cmd_titles.py
│   │   ├── cmd_sessions.py
│   │   ├── cmd_inspect.py
│   │   ├── cmd_map.py
│   │   ├── cmd_doctor.py
│   │   └── cmd_export.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── models.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── enums.py
│   │   ├── artifacts.py
│   │   ├── executable.py
│   │   ├── session.py
│   │   ├── title.py
│   │   ├── mapping.py
│   │   └── report.py
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── security_log.py
│   │   ├── prefetch.py
│   │   ├── userassist.py
│   │   ├── srum.py
│   │   ├── amcache.py
│   │   └── bam.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── orchestrator.py
│   │   └── registry.py
│   ├── normalize/
│   │   ├── __init__.py
│   │   ├── identity.py
│   │   ├── pathing.py
│   │   └── metadata.py
│   ├── classify/
│   │   ├── __init__.py
│   │   ├── rules.py
│   │   ├── heuristics.py
│   │   └── resolver.py
│   ├── merge/
│   │   ├── __init__.py
│   │   ├── events.py
│   │   ├── sessions.py
│   │   ├── titles.py
│   │   └── confidence.py
│   ├── store/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── schema.py
│   │   ├── repositories.py
│   │   └── migrations.py
│   ├── render/
│   │   ├── __init__.py
│   │   ├── console.py
│   │   ├── theme.py
│   │   ├── tables.py
│   │   ├── cards.py
│   │   ├── badges.py
│   │   ├── timeline.py
│   │   └── report_views.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── scanner.py
│   │   ├── reporter.py
│   │   ├── mapper.py
│   │   ├── inspector.py
│   │   ├── doctor.py
│   │   └── exporter.py
│   └── utils/
│       ├── __init__.py
│       ├── clock.py
│       ├── hashing.py
│       ├── platform.py
│       └── text.py
└── tests/
    ├── test_identity.py
    ├── test_merge_sessions.py
    ├── test_classification.py
    ├── test_report_render.py
    └── fixtures/
```

## Packaging and toolchain

Use:

* Python 3.12+
* `typer` for CLI
* `rich` for terminal UI
* `pydantic` or stdlib dataclasses for config validation
* `sqlite3` first, SQLAlchemy optional later
* `pytest` for tests

A minimal `pyproject.toml` shape:

```toml
[project]
name = "playtrace"
version = "0.1.0"
description = "Native Windows executable history and session analysis"
requires-python = ">=3.12"
dependencies = [
  "typer>=0.12",
  "rich>=13.7",
  "pydantic>=2.7",
]

[project.scripts]
playtrace = "playtrace.cli.app:app"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

## Python package layout

### `playtrace/__main__.py`

```python
from playtrace.cli.app import app

if __name__ == "__main__":
    app()
```

### `playtrace/version.py`

```python
__version__ = "0.1.0"
```

## CLI command definitions

### `playtrace/cli/app.py`

```python
from __future__ import annotations

import typer

from playtrace.cli.cmd_doctor import register_doctor
from playtrace.cli.cmd_export import register_export
from playtrace.cli.cmd_inspect import register_inspect
from playtrace.cli.cmd_map import register_map
from playtrace.cli.cmd_report import register_report
from playtrace.cli.cmd_scan import register_scan
from playtrace.cli.cmd_sessions import register_sessions
from playtrace.cli.cmd_titles import register_titles

app = typer.Typer(
    help="Native Windows executable history and session analysis.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

register_scan(app)
register_report(app)
register_titles(app)
register_sessions(app)
register_inspect(app)
register_map(app)
register_doctor(app)
register_export(app)
```

### `playtrace/cli/common.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

DatabaseOption = Annotated[
    Path,
    typer.Option(
        "--db",
        help="Path to the playtrace SQLite database.",
        dir_okay=False,
        writable=True,
        readable=True,
        resolve_path=True,
    ),
]

ConfigOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        help="Optional path to a config file.",
        dir_okay=False,
        resolve_path=True,
    ),
]

ThemeOption = Annotated[
    str,
    typer.Option("--theme", help="Theme name: midnight, amber, ice, mono."),
]

DensityOption = Annotated[
    str,
    typer.Option("--density", help="Density mode: compact, comfortable, cinematic."),
]
```

### `playtrace/cli/cmd_scan.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption
from playtrace.services.scanner import ScanRequest, ScannerService


def register_scan(app: typer.Typer) -> None:
    @app.command("scan")
    def scan(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        sources: list[str] = typer.Option(
            None,
            "--source",
            help="Limit scan to one or more sources: security_log, prefetch, userassist, srum, amcache, bam.",
        ),
        full: bool = typer.Option(False, "--full", help="Force a full rescan."),
    ) -> None:
        request = ScanRequest(db_path=db, config_path=config, sources=sources or [], full=full)
        ScannerService().run(request)
```

### `playtrace/cli/cmd_report.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import ConfigOption, DatabaseOption, DensityOption, ThemeOption
from playtrace.services.reporter import ReportRequest, ReporterService


def register_report(app: typer.Typer) -> None:
    @app.command("report")
    def report(
        db: DatabaseOption = Path("playtrace.db"),
        config: ConfigOption = None,
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
        limit: int = typer.Option(10, "--limit", min=1, help="Number of top titles to display."),
    ) -> None:
        request = ReportRequest(db_path=db, config_path=config, theme=theme, density=density, limit=limit)
        ReporterService().render_default(request)
```

### `playtrace/cli/cmd_titles.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, DensityOption, ThemeOption
from playtrace.services.reporter import TitlesRequest, ReporterService


def register_titles(app: typer.Typer) -> None:
    @app.command("titles")
    def titles(
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
        sort_by: str = typer.Option("runtime", "--sort", help="runtime, launches, last_seen, title"),
        classification: str | None = typer.Option(None, "--classification", help="Filter by title classification."),
        launcher: str | None = typer.Option(None, "--launcher", help="Filter by launcher."),
        limit: int = typer.Option(50, "--limit", min=1),
    ) -> None:
        request = TitlesRequest(
            db_path=db,
            theme=theme,
            density=density,
            sort_by=sort_by,
            classification=classification,
            launcher=launcher,
            limit=limit,
        )
        ReporterService().render_titles(request)
```

### `playtrace/cli/cmd_sessions.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, DensityOption, ThemeOption
from playtrace.services.reporter import SessionsRequest, ReporterService


def register_sessions(app: typer.Typer) -> None:
    @app.command("sessions")
    def sessions(
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
        title: str | None = typer.Option(None, "--title", help="Filter sessions by title."),
        days: int = typer.Option(30, "--days", min=1, help="Recent day window."),
        limit: int = typer.Option(100, "--limit", min=1),
    ) -> None:
        request = SessionsRequest(db_path=db, theme=theme, density=density, title=title, days=days, limit=limit)
        ReporterService().render_sessions(request)
```

### `playtrace/cli/cmd_inspect.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, DensityOption, ThemeOption
from playtrace.services.inspector import InspectRequest, InspectorService


def register_inspect(app: typer.Typer) -> None:
    @app.command("inspect")
    def inspect(
        target: str = typer.Argument(..., help="Title name, executable path, or internal ID."),
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
        density: DensityOption = "comfortable",
    ) -> None:
        request = InspectRequest(db_path=db, theme=theme, density=density, target=target)
        InspectorService().render(request)
```

### `playtrace/cli/cmd_map.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption
from playtrace.services.mapper import MapRequest, MapperService


def register_map(app: typer.Typer) -> None:
    @app.command("map")
    def map_title(
        target: str = typer.Argument(..., help="Executable path or executable ID."),
        title: str = typer.Option(..., "--title", help="User-facing title to assign."),
        classification: str | None = typer.Option(None, "--classification", help="Optional forced classification."),
        launcher: str | None = typer.Option(None, "--launcher", help="Optional launcher label."),
        ignore: bool = typer.Option(False, "--ignore", help="Suppress this executable from reports."),
        db: DatabaseOption = Path("playtrace.db"),
    ) -> None:
        request = MapRequest(
            db_path=db,
            target=target,
            title=title,
            classification=classification,
            launcher=launcher,
            ignore=ignore,
        )
        MapperService().apply(request)
```

### `playtrace/cli/cmd_doctor.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption, ThemeOption
from playtrace.services.doctor import DoctorRequest, DoctorService


def register_doctor(app: typer.Typer) -> None:
    @app.command("doctor")
    def doctor(
        db: DatabaseOption = Path("playtrace.db"),
        theme: ThemeOption = "midnight",
    ) -> None:
        request = DoctorRequest(db_path=db, theme=theme)
        DoctorService().render(request)
```

### `playtrace/cli/cmd_export.py`

```python
from __future__ import annotations

from pathlib import Path

import typer

from playtrace.cli.common import DatabaseOption
from playtrace.services.exporter import ExportRequest, ExporterService


def register_export(app: typer.Typer) -> None:
    @app.command("export")
    def export(
        db: DatabaseOption = Path("playtrace.db"),
        output: Path = typer.Option(..., "--output", help="Destination file path."),
        format: str = typer.Option("json", "--format", help="json, csv, markdown"),
    ) -> None:
        request = ExportRequest(db_path=db, output_path=output, format=format)
        ExporterService().run(request)
```

## First-pass data classes

### `playtrace/models/enums.py`

```python
from __future__ import annotations

from enum import Enum


class EvidenceStrength(str, Enum):
    EXACT = "exact"
    STRONG = "strong"
    INTERACTIVE = "interactive"
    ESTIMATED = "estimated"
    WEAK = "weak"
    UNKNOWN = "unknown"


class Classification(str, Enum):
    GAME = "game"
    LAUNCHER = "launcher"
    HELPER = "helper"
    RUNTIME = "runtime"
    OVERLAY = "overlay"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class SourceName(str, Enum):
    SECURITY_LOG = "security_log"
    PREFETCH = "prefetch"
    USERASSIST = "userassist"
    SRUM = "srum"
    AMCACHE = "amcache"
    BAM = "bam"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"
```

### `playtrace/models/artifacts.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from playtrace.models.enums import EvidenceStrength, SourceName


@dataclass(slots=True)
class ArtifactRecord:
    artifact_id: str
    source: SourceName
    observed_at: datetime | None
    user_sid: str | None
    exe_path: str | None
    exe_name: str | None
    process_id: int | None = None
    parent_process_id: int | None = None
    parent_exe_name: str | None = None
    launch_count: int | None = None
    run_timestamps: list[datetime] = field(default_factory=list)
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int | None = None
    foreground_seconds: int | None = None
    bytes_in: int | None = None
    bytes_out: int | None = None
    product_name: str | None = None
    file_description: str | None = None
    company_name: str | None = None
    signer: str | None = None
    original_filename: str | None = None
    sha1: str | None = None
    strength: EvidenceStrength = EvidenceStrength.UNKNOWN
    raw: dict[str, Any] = field(default_factory=dict)
```

### `playtrace/models/executable.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.enums import Classification, ConfidenceLevel


@dataclass(slots=True)
class ExecutableIdentity:
    exe_id: str
    normalized_key: str
    path: str | None
    filename: str | None
    original_filename: str | None
    product_name: str | None
    file_description: str | None
    signer: str | None
    company_name: str | None
    sha1: str | None
    classification: Classification = Classification.UNKNOWN
    classification_confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    ignored: bool = False
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    aliases: set[str] = field(default_factory=set)
    tags: set[str] = field(default_factory=set)
```

### `playtrace/models/session.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.enums import ConfidenceLevel


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    title_id: str | None
    exe_id: str
    user_sid: str | None
    started_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    foreground_seconds: int = 0
    bytes_in: int = 0
    bytes_out: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    evidence_sources: list[str] = field(default_factory=list)
    parent_chain: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
```

### `playtrace/models/title.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.enums import Classification, ConfidenceLevel


@dataclass(slots=True)
class RuntimeStats:
    confirmed_seconds: int = 0
    estimated_seconds: int = 0
    foreground_seconds: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN


@dataclass(slots=True)
class LaunchStats:
    confirmed: int = 0
    inferred: int = 0
    gui: int = 0
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN


@dataclass(slots=True)
class TitleAggregate:
    title_id: str
    title: str
    classification: Classification
    classification_confidence: ConfidenceLevel
    title_confidence: ConfidenceLevel
    launcher: str | None
    runtime: RuntimeStats = field(default_factory=RuntimeStats)
    launches: LaunchStats = field(default_factory=LaunchStats)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    executable_ids: list[str] = field(default_factory=list)
    evidence_sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
```

### `playtrace/models/mapping.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from playtrace.models.enums import Classification, ConfidenceLevel


@dataclass(slots=True)
class UserMapping:
    mapping_id: str
    target: str
    title: str
    classification: Classification | None
    launcher: str | None
    ignore: bool
    created_at: datetime
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
```

### `playtrace/models/report.py`

```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from playtrace.models.title import TitleAggregate
from playtrace.models.session import SessionRecord


@dataclass(slots=True)
class CoverageSummary:
    tracked_titles: int = 0
    confirmed_runtime_seconds: int = 0
    estimated_runtime_seconds: int = 0
    confirmed_sessions: int = 0
    unmapped_executables: int = 0


@dataclass(slots=True)
class ReportSnapshot:
    generated_at: datetime
    host_name: str
    coverage: CoverageSummary
    top_titles: list[TitleAggregate] = field(default_factory=list)
    recent_sessions: list[SessionRecord] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
```

## Parser interface

### `playtrace/parsers/base.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from playtrace.models.artifacts import ArtifactRecord


@dataclass(slots=True)
class ParseContext:
    host_name: str
    temp_dir: Path
    full_scan: bool = False


class ArtifactParser(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def parse(self, context: ParseContext) -> list[ArtifactRecord]: ...
```

## Ingest orchestration

### `playtrace/ingest/orchestrator.py`

```python
from __future__ import annotations

from dataclasses import dataclass

from playtrace.models.artifacts import ArtifactRecord
from playtrace.parsers.base import ArtifactParser, ParseContext


@dataclass(slots=True)
class IngestResult:
    artifacts: list[ArtifactRecord]
    warnings: list[str]


class IngestOrchestrator:
    def __init__(self, parsers: list[ArtifactParser]) -> None:
        self.parsers = parsers

    def run(self, context: ParseContext, selected_sources: set[str] | None = None) -> IngestResult:
        artifacts: list[ArtifactRecord] = []
        warnings: list[str] = []

        for parser in self.parsers:
            if selected_sources and parser.name not in selected_sources:
                continue
            if not parser.is_available():
                warnings.append(f"Source unavailable: {parser.name}")
                continue
            try:
                artifacts.extend(parser.parse(context))
            except Exception as exc:
                warnings.append(f"Failed to parse {parser.name}: {exc}")

        return IngestResult(artifacts=artifacts, warnings=warnings)
```

## Normalization interfaces

### `playtrace/normalize/identity.py`

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from playtrace.models.artifacts import ArtifactRecord
from playtrace.models.executable import ExecutableIdentity


@dataclass(slots=True)
class NormalizedArtifact:
    artifact: ArtifactRecord
    normalized_key: str


class IdentityNormalizer:
    def build_key(self, artifact: ArtifactRecord) -> str:
        if artifact.sha1:
            return f"sha1:{artifact.sha1.lower()}"

        basis = "|".join(
            part or ""
            for part in [
                artifact.exe_path,
                artifact.original_filename,
                artifact.product_name,
                artifact.signer,
            ]
        )
        digest = hashlib.sha1(basis.encode("utf-8", errors="ignore")).hexdigest()
        return f"soft:{digest}"

    def to_executable(self, artifact: ArtifactRecord) -> ExecutableIdentity:
        key = self.build_key(artifact)
        return ExecutableIdentity(
            exe_id=key,
            normalized_key=key,
            path=artifact.exe_path,
            filename=artifact.exe_name,
            original_filename=artifact.original_filename,
            product_name=artifact.product_name,
            file_description=artifact.file_description,
            signer=artifact.signer,
            company_name=artifact.company_name,
            sha1=artifact.sha1,
        )
```

## Merge stubs

### `playtrace/merge/sessions.py`

```python
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta

from playtrace.models.artifacts import ArtifactRecord
from playtrace.models.session import SessionRecord


@dataclass(slots=True)
class SessionMergeConfig:
    dedupe_window: timedelta = timedelta(minutes=2)


class SessionMerger:
    def __init__(self, config: SessionMergeConfig | None = None) -> None:
        self.config = config or SessionMergeConfig()

    def build_sessions(self, artifacts: list[ArtifactRecord], exe_id_lookup: dict[str, str]) -> list[SessionRecord]:
        # First-pass stub.
        # v1 behavior:
        # - exact session creation for artifacts with both started_at and ended_at
        # - partial sessions for launch-only artifacts
        sessions: list[SessionRecord] = []
        grouped: dict[str, list[ArtifactRecord]] = defaultdict(list)

        for artifact in artifacts:
            key = exe_id_lookup.get(artifact.artifact_id)
            if key:
                grouped[key].append(artifact)

        for exe_id, group in grouped.items():
            for index, artifact in enumerate(group, start=1):
                sessions.append(
                    SessionRecord(
                        session_id=f"{exe_id}:session:{index}",
                        title_id=None,
                        exe_id=exe_id,
                        user_sid=artifact.user_sid,
                        started_at=artifact.started_at or artifact.observed_at,
                        ended_at=artifact.ended_at,
                        duration_seconds=artifact.duration_seconds,
                        foreground_seconds=artifact.foreground_seconds or 0,
                        bytes_in=artifact.bytes_in or 0,
                        bytes_out=artifact.bytes_out or 0,
                        evidence_sources=[artifact.source.value],
                    )
                )

        return sessions
```

### `playtrace/merge/titles.py`

```python
from __future__ import annotations

from playtrace.models.executable import ExecutableIdentity
from playtrace.models.session import SessionRecord
from playtrace.models.title import LaunchStats, RuntimeStats, TitleAggregate
from playtrace.models.enums import Classification, ConfidenceLevel


class TitleAggregator:
    def build(self, executables: list[ExecutableIdentity], sessions: list[SessionRecord]) -> list[TitleAggregate]:
        title_map: dict[str, TitleAggregate] = {}

        for exe in executables:
            title_name = exe.product_name or (exe.filename.rsplit(".", 1)[0] if exe.filename else exe.exe_id)
            title_id = f"title:{title_name.lower().replace(' ', '_')}"
            title = title_map.setdefault(
                title_id,
                TitleAggregate(
                    title_id=title_id,
                    title=title_name,
                    classification=exe.classification or Classification.UNKNOWN,
                    classification_confidence=exe.classification_confidence or ConfidenceLevel.UNKNOWN,
                    title_confidence=ConfidenceLevel.MEDIUM,
                    launcher=None,
                ),
            )
            title.executable_ids.append(exe.exe_id)
            if exe.first_seen and (title.first_seen is None or exe.first_seen < title.first_seen):
                title.first_seen = exe.first_seen
            if exe.last_seen and (title.last_seen is None or exe.last_seen > title.last_seen):
                title.last_seen = exe.last_seen

        for session in sessions:
            for title in title_map.values():
                if session.exe_id in title.executable_ids:
                    if session.duration_seconds:
                        title.runtime.confirmed_seconds += session.duration_seconds
                    title.runtime.foreground_seconds += session.foreground_seconds
                    title.launches.confirmed += 1
                    break

        for title in title_map.values():
            title.runtime.confidence = ConfidenceLevel.HIGH if title.runtime.confirmed_seconds else ConfidenceLevel.UNKNOWN
            title.launches.confidence = ConfidenceLevel.HIGH if title.launches.confirmed else ConfidenceLevel.UNKNOWN

        return list(title_map.values())
```

## Service layer requests

### `playtrace/services/scanner.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ScanRequest:
    db_path: Path
    config_path: Path | None
    sources: list[str]
    full: bool = False


class ScannerService:
    def run(self, request: ScanRequest) -> None:
        raise NotImplementedError
```

### `playtrace/services/reporter.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ReportRequest:
    db_path: Path
    config_path: Path | None
    theme: str
    density: str
    limit: int


@dataclass(slots=True)
class TitlesRequest:
    db_path: Path
    theme: str
    density: str
    sort_by: str
    classification: str | None
    launcher: str | None
    limit: int


@dataclass(slots=True)
class SessionsRequest:
    db_path: Path
    theme: str
    density: str
    title: str | None
    days: int
    limit: int


class ReporterService:
    def render_default(self, request: ReportRequest) -> None:
        raise NotImplementedError

    def render_titles(self, request: TitlesRequest) -> None:
        raise NotImplementedError

    def render_sessions(self, request: SessionsRequest) -> None:
        raise NotImplementedError
```

### `playtrace/services/inspector.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class InspectRequest:
    db_path: Path
    theme: str
    density: str
    target: str


class InspectorService:
    def render(self, request: InspectRequest) -> None:
        raise NotImplementedError
```

### `playtrace/services/mapper.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class MapRequest:
    db_path: Path
    target: str
    title: str
    classification: str | None
    launcher: str | None
    ignore: bool


class MapperService:
    def apply(self, request: MapRequest) -> None:
        raise NotImplementedError
```

### `playtrace/services/doctor.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class DoctorRequest:
    db_path: Path
    theme: str


class DoctorService:
    def render(self, request: DoctorRequest) -> None:
        raise NotImplementedError
```

### `playtrace/services/exporter.py`

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExportRequest:
    db_path: Path
    output_path: Path
    format: str


class ExporterService:
    def run(self, request: ExportRequest) -> None:
        raise NotImplementedError
```

## Rendering foundation

### `playtrace/render/console.py`

```python
from __future__ import annotations

from rich.console import Console


def build_console() -> Console:
    return Console(highlight=False, soft_wrap=False)
```

### `playtrace/render/theme.py`

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Theme:
    name: str
    accent: str
    success: str
    warning: str
    danger: str
    dim: str
    text: str


THEMES: dict[str, Theme] = {
    "midnight": Theme("midnight", "cyan", "green", "yellow", "red", "bright_black", "white"),
    "amber": Theme("amber", "bright_yellow", "green", "yellow", "red", "bright_black", "white"),
    "ice": Theme("ice", "bright_cyan", "green", "yellow", "red", "bright_black", "white"),
    "mono": Theme("mono", "white", "white", "white", "white", "bright_black", "white"),
}
```

## Store bootstrap

### `playtrace/store/schema.py`

```python
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS executables (
    exe_id TEXT PRIMARY KEY,
    normalized_key TEXT NOT NULL,
    path TEXT,
    filename TEXT,
    original_filename TEXT,
    product_name TEXT,
    file_description TEXT,
    signer TEXT,
    company_name TEXT,
    sha1 TEXT,
    classification TEXT NOT NULL,
    classification_confidence TEXT NOT NULL,
    ignored INTEGER NOT NULL DEFAULT 0,
    first_seen TEXT,
    last_seen TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    title_id TEXT,
    exe_id TEXT NOT NULL,
    user_sid TEXT,
    started_at TEXT,
    ended_at TEXT,
    duration_seconds INTEGER,
    foreground_seconds INTEGER NOT NULL DEFAULT 0,
    bytes_in INTEGER NOT NULL DEFAULT 0,
    bytes_out INTEGER NOT NULL DEFAULT 0,
    confidence TEXT NOT NULL,
    evidence_sources TEXT NOT NULL,
    parent_chain TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS titles (
    title_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    classification TEXT NOT NULL,
    classification_confidence TEXT NOT NULL,
    title_confidence TEXT NOT NULL,
    launcher TEXT,
    confirmed_seconds INTEGER NOT NULL DEFAULT 0,
    estimated_seconds INTEGER NOT NULL DEFAULT 0,
    foreground_seconds INTEGER NOT NULL DEFAULT 0,
    runtime_confidence TEXT NOT NULL,
    launches_confirmed INTEGER NOT NULL DEFAULT 0,
    launches_inferred INTEGER NOT NULL DEFAULT 0,
    launches_gui INTEGER NOT NULL DEFAULT 0,
    launches_confidence TEXT NOT NULL,
    first_seen TEXT,
    last_seen TEXT,
    evidence_sources TEXT NOT NULL,
    tags TEXT NOT NULL,
    notes TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mappings (
    mapping_id TEXT PRIMARY KEY,
    target TEXT NOT NULL,
    title TEXT NOT NULL,
    classification TEXT,
    launcher TEXT,
    ignore INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    confidence TEXT NOT NULL
);
"""
```

## BUILD ORDER

Build in this order:

1. `doctor` command
2. parser base + stub parsers
3. `scan` command skeleton
4. identity normalization
5. SQLite schema bootstrap
6. `report` with mock rows first
7. exact session merge from security log parser
8. title aggregation
9. `inspect`
10. `map`

## RULES

Keep these layers clean:

* parsers do not classify
* classifiers do not render
* renderers do not query raw artifact formats
* services coordinate, models carry data

That separation will make the project much easier to evolve when you add real forensic parsing later.
