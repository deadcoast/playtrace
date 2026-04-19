from __future__ import annotations

from dataclasses import dataclass
from typing import Any


UNSET = object()


@dataclass(slots=True)
class PresentationSettings:
    theme: str | None = None
    density: str | None = None


@dataclass(slots=True)
class ReconstructionSettings:
    session_merge_dedupe_window_minutes: int = 2
    duplicate_auto_merge: bool = False
    duplicate_similarity_threshold: float = 0.85
    minimum_evidence_confidence: str = "low"
    default_sources: list[str] | None = None
    classification_overrides: dict[str, str] | None = None


@dataclass(slots=True)
class RawScanInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    sources: list[str] | object = UNSET
    full: bool | object = UNSET


@dataclass(slots=True)
class RawMeInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    refresh: bool | object = UNSET


@dataclass(slots=True)
class RawReportInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    limit: int | object = UNSET


@dataclass(slots=True)
class RawDoctorInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    severity: str | object = UNSET


@dataclass(slots=True)
class RawTitlesInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    limit: int | object = UNSET
    sort_by: str | object = UNSET
    classification: str | object = UNSET
    launcher: str | object = UNSET


@dataclass(slots=True)
class RawSessionsInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    days: int | object = UNSET
    limit: int | object = UNSET
    title: str | object = UNSET


@dataclass(slots=True)
class RawInspectInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    depth: str | object = UNSET


@dataclass(slots=True)
class RawSourcesInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    depth: str | object = UNSET


@dataclass(slots=True)
class RawMapInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    auto: bool | object = UNSET


@dataclass(slots=True)
class RawExportInput:
    theme: str | object = UNSET
    density: str | object = UNSET
    format: str | object = UNSET
    scope: str | object = UNSET


@dataclass(slots=True)
class ResolvedSettingsBase:
    profile_name: str
    presentation: PresentationSettings
    reconstruction: ReconstructionSettings


@dataclass(slots=True)
class ResolvedScanSettings(ResolvedSettingsBase):
    full: bool = False
    sources: list[str] | None = None


@dataclass(slots=True)
class ResolvedMeSettings(ResolvedSettingsBase):
    refresh: bool = False


@dataclass(slots=True)
class ResolvedReportSettings(ResolvedSettingsBase):
    limit: int | None = None


@dataclass(slots=True)
class ResolvedDoctorSettings(ResolvedSettingsBase):
    severity: str | None = None


@dataclass(slots=True)
class ResolvedTitlesSettings(ResolvedSettingsBase):
    limit: int | None = None
    sort_by: str | None = None
    classification: str | None = None
    launcher: str | None = None


@dataclass(slots=True)
class ResolvedSessionsSettings(ResolvedSettingsBase):
    days: int | None = None
    limit: int | None = None
    title: str | None = None


@dataclass(slots=True)
class ResolvedInspectSettings(ResolvedSettingsBase):
    depth: str | None = None


@dataclass(slots=True)
class ResolvedSourcesSettings(ResolvedSettingsBase):
    depth: str | None = None


@dataclass(slots=True)
class ResolvedMapSettings(ResolvedSettingsBase):
    auto: bool | None = None


@dataclass(slots=True)
class ResolvedExportSettings(ResolvedSettingsBase):
    format: str | None = None
    scope: str | None = None


def is_unset(value: Any) -> bool:
    return value is UNSET
