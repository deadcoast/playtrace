from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from playtrace.models.enums import SourceName


@dataclass(slots=True)
class ReconstructionConfig:
    session_merge_dedupe_window_minutes: int = 2
    duplicate_auto_merge: bool = False
    duplicate_similarity_threshold: float = 0.85
    minimum_evidence_confidence: str = "low"


@dataclass(slots=True)
class ClassificationConfig:
    overrides: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class DefaultsConfig:
    active_profile: str = "ready"
    theme: str | None = None
    density: str | None = None
    default_sources: list[str] = field(default_factory=list)
    reconstruction: ReconstructionConfig = field(default_factory=ReconstructionConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)
    scan: ScanConfig = field(default_factory=lambda: ScanConfig())
    me: MeConfig = field(default_factory=lambda: MeConfig())
    report: ReportConfig = field(default_factory=lambda: ReportConfig())
    doctor: DoctorConfig = field(default_factory=lambda: DoctorConfig())
    titles: TitlesConfig = field(default_factory=lambda: TitlesConfig())
    sessions: SessionsConfig = field(default_factory=lambda: SessionsConfig())
    inspect: InspectConfig = field(default_factory=lambda: InspectConfig())
    sources: SourcesConfig = field(default_factory=lambda: SourcesConfig())
    map: MapConfig = field(default_factory=lambda: MapConfig())
    export: ExportConfig = field(default_factory=lambda: ExportConfig())


@dataclass(slots=True)
class CommandConfig:
    theme: str | None = None
    density: str | None = None


@dataclass(slots=True)
class ScanConfig(CommandConfig):
    full: bool = False


@dataclass(slots=True)
class MeConfig(CommandConfig):
    refresh: bool = False


@dataclass(slots=True)
class ReportConfig(CommandConfig):
    limit: int | None = 10


@dataclass(slots=True)
class DoctorConfig(CommandConfig):
    severity: str | None = "low"


@dataclass(slots=True)
class TitlesConfig(CommandConfig):
    limit: int | None = 50
    sort_by: str | None = "runtime"
    classification: str | None = None
    launcher: str | None = None


@dataclass(slots=True)
class SessionsConfig(CommandConfig):
    days: int | None = 30
    limit: int | None = 100
    title: str | None = None


@dataclass(slots=True)
class InspectConfig(CommandConfig):
    depth: str | None = "summary"


@dataclass(slots=True)
class SourcesConfig(CommandConfig):
    depth: str | None = "summary"


@dataclass(slots=True)
class MapConfig(CommandConfig):
    auto: bool | None = None


@dataclass(slots=True)
class ExportConfig(CommandConfig):
    format: str | None = "json"
    scope: str | None = "entity"


@dataclass(slots=True)
class ProfileConfig:
    scan: ScanConfig = field(default_factory=ScanConfig)
    me: MeConfig = field(default_factory=MeConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    doctor: DoctorConfig = field(default_factory=DoctorConfig)
    titles: TitlesConfig = field(default_factory=TitlesConfig)
    sessions: SessionsConfig = field(default_factory=SessionsConfig)
    inspect: InspectConfig = field(default_factory=InspectConfig)
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    map: MapConfig = field(default_factory=MapConfig)
    export: ExportConfig = field(default_factory=ExportConfig)


@dataclass(slots=True, init=False)
class ConfigModel:
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    me: MeConfig = field(default_factory=MeConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    doctor: DoctorConfig = field(default_factory=DoctorConfig)
    titles: TitlesConfig = field(default_factory=TitlesConfig)
    sessions: SessionsConfig = field(default_factory=SessionsConfig)
    inspect: InspectConfig = field(default_factory=InspectConfig)
    sources: SourcesConfig = field(default_factory=SourcesConfig)
    map: MapConfig = field(default_factory=MapConfig)
    export: ExportConfig = field(default_factory=ExportConfig)
    profiles: dict[str, ProfileConfig] = field(default_factory=dict)

    def __init__(
        self,
        *,
        defaults: DefaultsConfig | None = None,
        scan: ScanConfig | None = None,
        me: MeConfig | None = None,
        report: ReportConfig | None = None,
        doctor: DoctorConfig | None = None,
        titles: TitlesConfig | None = None,
        sessions: SessionsConfig | None = None,
        inspect: InspectConfig | None = None,
        sources: SourcesConfig | None = None,
        map: MapConfig | None = None,
        export: ExportConfig | None = None,
        profiles: dict[str, ProfileConfig] | None = None,
        session_merge_dedupe_window_minutes: int | None = None,
        default_sources: list[str] | None = None,
        classification_overrides: dict[str, str] | None = None,
    ) -> None:
        resolved_defaults = deepcopy(defaults) if defaults is not None else DefaultsConfig()
        if session_merge_dedupe_window_minutes is not None:
            resolved_defaults.reconstruction.session_merge_dedupe_window_minutes = (
                session_merge_dedupe_window_minutes
            )
        if default_sources is not None:
            resolved_defaults.default_sources = list(default_sources)
        if classification_overrides is not None:
            resolved_defaults.classification.overrides = dict(classification_overrides)

        self.defaults = resolved_defaults
        self.scan = deepcopy(scan) if scan is not None else ScanConfig()
        self.me = deepcopy(me) if me is not None else MeConfig()
        self.report = deepcopy(report) if report is not None else ReportConfig()
        self.doctor = deepcopy(doctor) if doctor is not None else DoctorConfig()
        self.titles = deepcopy(titles) if titles is not None else TitlesConfig()
        self.sessions = deepcopy(sessions) if sessions is not None else SessionsConfig()
        self.inspect = deepcopy(inspect) if inspect is not None else InspectConfig()
        self.sources = deepcopy(sources) if sources is not None else SourcesConfig()
        self.map = deepcopy(map) if map is not None else MapConfig()
        self.export = deepcopy(export) if export is not None else ExportConfig()
        self.profiles = deepcopy(profiles) if profiles is not None else {}
        self.__post_init__()

    def __post_init__(self) -> None:
        self._validate_merge_window()
        self._validate_sources()

    @property
    def session_merge_dedupe_window_minutes(self) -> int:
        return self.defaults.reconstruction.session_merge_dedupe_window_minutes

    @property
    def default_sources(self) -> list[str]:
        return self.defaults.default_sources

    @property
    def classification_overrides(self) -> dict[str, str]:
        return self.defaults.classification.overrides

    def _validate_merge_window(self) -> None:
        if self.defaults.reconstruction.session_merge_dedupe_window_minutes <= 0:
            raise ValueError("session_merge_dedupe_window_minutes must be positive")

    def _validate_sources(self) -> None:
        for source in self.defaults.default_sources:
            try:
                SourceName(source)
            except ValueError as exc:
                raise ValueError(f"default_sources contains invalid source: {source}") from exc

