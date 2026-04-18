from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

from playtrace.config.models import (
    ClassificationConfig,
    ConfigModel,
    DefaultsConfig,
    DoctorConfig,
    ExportConfig,
    InspectConfig,
    MapConfig,
    MeConfig,
    ProfileConfig,
    ReconstructionConfig,
    ReportConfig,
    ScanConfig,
    SessionsConfig,
    SourcesConfig,
    TitlesConfig,
)


class ConfigLoader:
    def load(self, path: Path | None = None) -> ConfigModel:
        if path is None or not path.exists():
            return ConfigModel()

        data = self._parse_toml(path)
        return ConfigModel(
            defaults=self._build_defaults(data),
            scan=self._build_scan(data.get("scan")),
            me=self._build_me(data.get("me")),
            report=self._build_report(data.get("report")),
            doctor=self._build_doctor(data.get("doctor")),
            titles=self._build_titles(data.get("titles")),
            sessions=self._build_sessions(data.get("sessions")),
            inspect=self._build_inspect(data.get("inspect")),
            sources=self._build_sources(data.get("sources")),
            map=self._build_map(data.get("map")),
            export=self._build_export(data.get("export")),
            profiles=self._build_profiles(data.get("profiles")),
        )

    def _parse_toml(self, path: Path) -> dict[str, Any]:
        with path.open("rb") as handle:
            return tomllib.load(handle)

    def _build_defaults(self, data: dict[str, Any]) -> DefaultsConfig:
        defaults = self._table(data.get("defaults"))
        reconstruction = self._table(defaults.get("reconstruction"))
        classification = self._table(defaults.get("classification"))
        session = self._table(data.get("session"))
        sources = self._table(data.get("sources"))
        legacy_classification = self._table(data.get("classification"))

        merge_window = self._coalesce(
            reconstruction,
            "session_merge_dedupe_window_minutes",
            session.get("merge_dedupe_window_minutes"),
            data.get("session_merge_dedupe_window_minutes"),
            fallback=2,
        )
        default_sources = self._coalesce_list(
            defaults,
            "default_sources",
            sources.get("default"),
            data.get("default_sources"),
        )
        overrides = self._coalesce_dict(
            classification,
            "overrides",
            legacy_classification.get("overrides"),
            data.get("classification_overrides"),
        )

        return DefaultsConfig(
            active_profile=defaults.get("active_profile", "ready"),
            theme=defaults.get("theme"),
            density=defaults.get("density"),
            default_sources=default_sources,
            reconstruction=ReconstructionConfig(
                session_merge_dedupe_window_minutes=merge_window,
                duplicate_auto_merge=bool(reconstruction.get("duplicate_auto_merge", False)),
                duplicate_similarity_threshold=float(
                    reconstruction.get("duplicate_similarity_threshold", 0.85)
                ),
                minimum_evidence_confidence=reconstruction.get(
                    "minimum_evidence_confidence",
                    "low",
                ),
            ),
            classification=ClassificationConfig(overrides=overrides),
            scan=self._build_scan(defaults.get("scan")),
            me=self._build_me(defaults.get("me")),
            report=self._build_report(defaults.get("report")),
            doctor=self._build_doctor(defaults.get("doctor")),
            titles=self._build_titles(defaults.get("titles")),
            sessions=self._build_sessions(defaults.get("sessions")),
            inspect=self._build_inspect(defaults.get("inspect")),
            sources=self._build_sources(defaults.get("sources")),
            map=self._build_map(defaults.get("map")),
            export=self._build_export(defaults.get("export")),
        )

    def _build_profiles(self, value: Any) -> dict[str, ProfileConfig]:
        tables = self._table(value)
        profiles: dict[str, ProfileConfig] = {}
        for name, entry in tables.items():
            profile_table = self._table(entry)
            profiles[name] = ProfileConfig(
                scan=self._build_scan(profile_table.get("scan")),
                me=self._build_me(profile_table.get("me")),
                report=self._build_report(profile_table.get("report")),
                doctor=self._build_doctor(profile_table.get("doctor")),
                titles=self._build_titles(profile_table.get("titles")),
                sessions=self._build_sessions(profile_table.get("sessions")),
                inspect=self._build_inspect(profile_table.get("inspect")),
                sources=self._build_sources(profile_table.get("sources")),
                map=self._build_map(profile_table.get("map")),
                export=self._build_export(profile_table.get("export")),
            )
        return profiles

    def _build_scan(self, value: Any) -> ScanConfig:
        table = self._table(value)
        return ScanConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            full=table.get("full", False),
        )

    def _build_me(self, value: Any) -> MeConfig:
        table = self._table(value)
        return MeConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            refresh=table.get("refresh", False),
        )

    def _build_report(self, value: Any) -> ReportConfig:
        table = self._table(value)
        return ReportConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            limit=table.get("limit", 10),
        )

    def _build_doctor(self, value: Any) -> DoctorConfig:
        table = self._table(value)
        return DoctorConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            severity=table.get("severity", "low"),
        )

    def _build_titles(self, value: Any) -> TitlesConfig:
        table = self._table(value)
        return TitlesConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            limit=table.get("limit", 50),
            sort_by=table.get("sort_by", "runtime"),
            classification=table.get("classification"),
            launcher=table.get("launcher"),
        )

    def _build_sessions(self, value: Any) -> SessionsConfig:
        table = self._table(value)
        return SessionsConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            days=table.get("days", 30),
            limit=table.get("limit", 100),
            title=table.get("title"),
        )

    def _build_inspect(self, value: Any) -> InspectConfig:
        table = self._table(value)
        return InspectConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            depth=table.get("depth", "summary"),
        )

    def _build_sources(self, value: Any) -> SourcesConfig:
        table = self._table(value)
        return SourcesConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            depth=table.get("depth", "summary"),
        )

    def _build_map(self, value: Any) -> MapConfig:
        table = self._table(value)
        return MapConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            auto=table.get("auto"),
        )

    def _build_export(self, value: Any) -> ExportConfig:
        table = self._table(value)
        return ExportConfig(
            theme=table.get("theme"),
            density=table.get("density"),
            format=table.get("format", "json"),
        )

    def _table(self, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    def _coalesce(
        self,
        primary: dict[str, Any],
        key: str,
        secondary: Any,
        tertiary: Any,
        *,
        fallback: Any,
    ) -> Any:
        if key in primary:
            return primary[key]
        if secondary is not None:
            return secondary
        if tertiary is not None:
            return tertiary
        return fallback

    def _coalesce_list(
        self,
        primary: dict[str, Any],
        key: str,
        secondary: Any,
        tertiary: Any,
    ) -> list[str]:
        if key in primary:
            return list(primary.get(key) or [])
        if secondary is not None:
            return list(secondary)
        if tertiary is not None:
            return list(tertiary)
        return []

    def _coalesce_dict(
        self,
        primary: dict[str, Any],
        key: str,
        secondary: Any,
        tertiary: Any,
    ) -> dict[str, str]:
        if key in primary:
            return dict(primary.get(key) or {})
        if secondary is not None:
            return dict(secondary)
        if tertiary is not None:
            return dict(tertiary)
        return {}
