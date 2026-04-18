from __future__ import annotations

from dataclasses import replace
from typing import Any

from playtrace.config.models import ConfigModel, ProfileConfig
from playtrace.config.runtime import (
    RawDoctorInput,
    RawExportInput,
    RawInspectInput,
    RawMapInput,
    RawMeInput,
    RawReportInput,
    RawScanInput,
    RawSessionsInput,
    RawSourcesInput,
    RawTitlesInput,
    ReconstructionSettings,
    PresentationSettings,
    ResolvedDoctorSettings,
    ResolvedExportSettings,
    ResolvedInspectSettings,
    ResolvedMapSettings,
    ResolvedMeSettings,
    ResolvedReportSettings,
    ResolvedScanSettings,
    ResolvedSessionsSettings,
    ResolvedSourcesSettings,
    ResolvedTitlesSettings,
    is_unset,
)


class ConfigResolver:
    def __init__(self) -> None:
        self._built_in = ConfigModel(profiles={"ready": ProfileConfig()})

    def resolve_scan(
        self,
        *,
        config: ConfigModel,
        cli: RawScanInput,
        spec_name: str | None,
    ) -> ResolvedScanSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedScanSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "scan", cli),
            reconstruction=self._reconstruction(config, cli),
            full=self._value(
                self._built_in.defaults.scan.full,
                config.defaults.scan.full,
                profile.scan.full,
                config.scan.full,
                cli.full,
            ),
            sources=self._value(
                self._built_in.defaults.default_sources,
                config.defaults.default_sources,
                self._built_in.defaults.default_sources,
                config.defaults.default_sources,
                cli.sources,
            ),
        )

    def resolve_me(
        self,
        *,
        config: ConfigModel,
        cli: RawMeInput,
        spec_name: str | None,
    ) -> ResolvedMeSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedMeSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "me", cli),
            reconstruction=self._reconstruction(config, cli),
            refresh=self._value(
                self._built_in.defaults.me.refresh,
                config.defaults.me.refresh,
                profile.me.refresh,
                config.me.refresh,
                cli.refresh,
            ),
        )

    def resolve_report(
        self,
        *,
        config: ConfigModel,
        cli: RawReportInput,
        spec_name: str | None,
    ) -> ResolvedReportSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedReportSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "report", cli),
            reconstruction=self._reconstruction(config, cli),
            limit=self._value(
                self._built_in.defaults.report.limit,
                config.defaults.report.limit,
                profile.report.limit,
                config.report.limit,
                cli.limit,
            ),
        )

    def resolve_doctor(
        self,
        *,
        config: ConfigModel,
        cli: RawDoctorInput,
        spec_name: str | None,
    ) -> ResolvedDoctorSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedDoctorSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "doctor", cli),
            reconstruction=self._reconstruction(config, cli),
            severity=self._value(
                self._built_in.defaults.doctor.severity,
                config.defaults.doctor.severity,
                profile.doctor.severity,
                config.doctor.severity,
                cli.severity,
            ),
        )

    def resolve_titles(
        self,
        *,
        config: ConfigModel,
        cli: RawTitlesInput,
        spec_name: str | None,
    ) -> ResolvedTitlesSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedTitlesSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "titles", cli),
            reconstruction=self._reconstruction(config, cli),
            limit=self._value(
                self._built_in.defaults.titles.limit,
                config.defaults.titles.limit,
                profile.titles.limit,
                config.titles.limit,
                cli.limit,
            ),
            sort_by=self._value(
                self._built_in.defaults.titles.sort_by,
                config.defaults.titles.sort_by,
                profile.titles.sort_by,
                config.titles.sort_by,
                cli.sort_by,
            ),
            classification=self._value(
                self._built_in.defaults.titles.classification,
                config.defaults.titles.classification,
                profile.titles.classification,
                config.titles.classification,
                cli.classification,
            ),
            launcher=self._value(
                self._built_in.defaults.titles.launcher,
                config.defaults.titles.launcher,
                profile.titles.launcher,
                config.titles.launcher,
                cli.launcher,
            ),
        )

    def resolve_sessions(
        self,
        *,
        config: ConfigModel,
        cli: RawSessionsInput,
        spec_name: str | None,
    ) -> ResolvedSessionsSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedSessionsSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "sessions", cli),
            reconstruction=self._reconstruction(config, cli),
            days=self._value(
                self._built_in.defaults.sessions.days,
                config.defaults.sessions.days,
                profile.sessions.days,
                config.sessions.days,
                cli.days,
            ),
            limit=self._value(
                self._built_in.defaults.sessions.limit,
                config.defaults.sessions.limit,
                profile.sessions.limit,
                config.sessions.limit,
                cli.limit,
            ),
            title=self._value(
                self._built_in.defaults.sessions.title,
                config.defaults.sessions.title,
                profile.sessions.title,
                config.sessions.title,
                cli.title,
            ),
        )

    def resolve_inspect(
        self,
        *,
        config: ConfigModel,
        cli: RawInspectInput,
        spec_name: str | None,
    ) -> ResolvedInspectSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedInspectSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "inspect", cli),
            reconstruction=self._reconstruction(config, cli),
            depth=self._value(
                self._built_in.defaults.inspect.depth,
                config.defaults.inspect.depth,
                profile.inspect.depth,
                config.inspect.depth,
                cli.depth,
            ),
        )

    def resolve_sources(
        self,
        *,
        config: ConfigModel,
        cli: RawSourcesInput,
        spec_name: str | None,
    ) -> ResolvedSourcesSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedSourcesSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "sources", cli),
            reconstruction=self._reconstruction(config, cli),
            depth=self._value(
                self._built_in.defaults.sources.depth,
                config.defaults.sources.depth,
                profile.sources.depth,
                config.sources.depth,
                cli.depth,
            ),
        )

    def resolve_map(
        self,
        *,
        config: ConfigModel,
        cli: RawMapInput,
        spec_name: str | None,
    ) -> ResolvedMapSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedMapSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "map", cli),
            reconstruction=self._reconstruction(config, cli),
            auto=self._value(
                self._built_in.defaults.map.auto,
                config.defaults.map.auto,
                profile.map.auto,
                config.map.auto,
                cli.auto,
            ),
        )

    def resolve_export(
        self,
        *,
        config: ConfigModel,
        cli: RawExportInput,
        spec_name: str | None,
    ) -> ResolvedExportSettings:
        profile_name, profile = self._resolve_profile(config, spec_name)
        return ResolvedExportSettings(
            profile_name=profile_name,
            presentation=self._presentation(config, profile, "export", cli),
            reconstruction=self._reconstruction(config, cli),
            format=self._value(
                self._built_in.defaults.export.format,
                config.defaults.export.format,
                profile.export.format,
                config.export.format,
                cli.format,
            ),
            scope=self._value(
                self._built_in.defaults.export.scope,
                config.defaults.export.scope,
                profile.export.scope,
                config.export.scope,
                cli.scope,
            ),
        )

    def _resolve_profile(
        self,
        config: ConfigModel,
        spec_name: str | None,
    ) -> tuple[str, ProfileConfig]:
        selected = spec_name or config.defaults.active_profile or "ready"
        if selected in config.profiles:
            return selected, config.profiles[selected]
        return "ready", self._built_in.profiles["ready"]

    def _presentation(
        self,
        config: ConfigModel,
        profile: ProfileConfig,
        command_name: str,
        cli: Any,
    ) -> PresentationSettings:
        built_in_command = getattr(self._built_in.defaults, command_name)
        config_default_command = getattr(config.defaults, command_name)
        profile_command = getattr(profile, command_name)
        command = getattr(config, command_name)
        return PresentationSettings(
            theme=self._value(
                self._built_in.defaults.theme,
                config.defaults.theme,
                profile_command.theme,
                command.theme,
                getattr(cli, "theme", None),
            ),
            density=self._value(
                self._built_in.defaults.density,
                config.defaults.density,
                profile_command.density,
                command.density,
                getattr(cli, "density", None),
            ),
        )

    def _reconstruction(self, config: ConfigModel, cli: Any) -> ReconstructionSettings:
        return ReconstructionSettings(
            session_merge_dedupe_window_minutes=(
                config.defaults.reconstruction.session_merge_dedupe_window_minutes
            ),
            duplicate_auto_merge=config.defaults.reconstruction.duplicate_auto_merge,
            duplicate_similarity_threshold=config.defaults.reconstruction.duplicate_similarity_threshold,
            minimum_evidence_confidence=config.defaults.reconstruction.minimum_evidence_confidence,
            default_sources=list(config.defaults.default_sources),
            classification_overrides=dict(config.defaults.classification.overrides),
        )

    def _value(self, *candidates: Any) -> Any:
        result = None
        for candidate in candidates:
            if not is_unset(candidate) and candidate is not None:
                result = candidate
        return result
