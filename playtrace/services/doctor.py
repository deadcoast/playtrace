from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from playtrace.models.doctor import DoctorSnapshot
from playtrace.render.console import build_console
from playtrace.render.doctor_views import render_doctor
from playtrace.render.theme import get_theme
from playtrace.services.audit import AuditRequest, AuditService


@dataclass(slots=True)
class DoctorRequest:
    db_path: Path
    theme: str


class DoctorService:
    def __init__(self, audit_service: AuditService | object | None = None) -> None:
        self.audit_service = audit_service or AuditService()

    def load(self, request: DoctorRequest) -> DoctorSnapshot:
        return self.audit_service.load(AuditRequest(db_path=request.db_path))

    def render(self, request: DoctorRequest) -> DoctorSnapshot:
        console = build_console()
        theme = get_theme(request.theme)
        snapshot = self.load(request)
        render_doctor(console, theme, snapshot)
        return snapshot
