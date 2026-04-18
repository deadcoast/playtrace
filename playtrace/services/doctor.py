from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playtrace.config.loader import ConfigLoader
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import RawDoctorInput, UNSET
from playtrace.models.doctor import DoctorSnapshot
from playtrace.render.console import build_console
from playtrace.render.doctor_views import render_doctor
from playtrace.render.repair_views import render_repair_preview
from playtrace.render.theme import get_theme
from playtrace.services.audit import AuditRequest, AuditService
from playtrace.services.rebuild import RebuildService


@dataclass(slots=True, init=False)
class DoctorRequest:
    db_path: Path
    config_path: Path | None
    spec_name: str | None
    raw: RawDoctorInput
    repair: bool
    yes: bool

    def __init__(
        self,
        *,
        db_path: Path,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawDoctorInput | None = None,
        theme: str | None = None,
        density: str | None = None,
        severity: str | None = None,
        repair: bool = False,
        yes: bool = False,
    ) -> None:
        self.db_path = db_path
        self.config_path = config_path
        self.spec_name = spec_name
        self.repair = repair
        self.yes = yes
        self.raw = raw or RawDoctorInput(
            theme=theme if theme is not None else UNSET,
            density=density if density is not None else UNSET,
            severity=severity if severity is not None else UNSET,
        )


class DoctorService:
    def __init__(
        self,
        audit_service: AuditService | object | None = None,
        rebuild_service: RebuildService | None = None,
        *,
        config_loader: ConfigLoader | None = None,
        resolver: ConfigResolver | None = None,
    ) -> None:
        self.audit_service = audit_service or AuditService()
        self.rebuild_service = rebuild_service or RebuildService()
        self.config_loader = config_loader or ConfigLoader()
        self.resolver = resolver or ConfigResolver()

    def load(self, request: DoctorRequest) -> DoctorSnapshot:
        return self.audit_service.load(AuditRequest(db_path=request.db_path))

    def render(self, request: DoctorRequest) -> DoctorSnapshot:
        resolved = self._resolve(request)
        console = build_console()
        theme = get_theme(resolved.presentation.theme)
        snapshot = self.load(request)
        render_doctor(console, theme, snapshot)
        if request.repair:
            preview = self.rebuild_service.plan(request.db_path, settings=resolved.reconstruction)
            render_repair_preview(console, theme, preview, title="Repair Preview")
            if request.yes:
                self.rebuild_service.apply(
                    request.db_path,
                    preview=preview,
                    confirmed=True,
                    settings=resolved.reconstruction,
                )
        return snapshot

    def _resolve(self, request: DoctorRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_doctor(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )
