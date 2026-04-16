from __future__ import annotations

import ctypes
import os
import platform
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from playtrace.models.doctor import DoctorFinding, DoctorSnapshot
from playtrace.store.db import Database


@dataclass(slots=True)
class AuditRequest:
    db_path: Path


class AuditService:
    def __init__(
        self,
        *,
        platform_name: str | None = None,
        os_name: str | None = None,
        admin_checker: Callable[[], bool] | None = None,
        path_status: Callable[[str], str] | None = None,
    ) -> None:
        self._platform_name = platform_name
        self._os_name = os_name
        self._admin_checker = admin_checker or self._is_admin
        self._path_status = path_status or self._status_for_path

    def load(self, request: AuditRequest) -> DoctorSnapshot:
        db = Database(request.db_path)
        db.bootstrap()
        return DoctorSnapshot(
            environment_findings=self._environment_findings(db),
            data_findings=self._data_findings(db),
        )

    def _environment_findings(self, db: Database) -> list[DoctorFinding]:
        findings: list[DoctorFinding] = []
        platform_name = self._platform_name or platform.system()
        os_name = self._os_name or os.name

        if platform_name != "Windows" or os_name != "nt":
            findings.append(
                DoctorFinding(
                    severity="error",
                    code="not-windows",
                    summary="Playtrace requires a Windows host for native evidence collection.",
                    remediation=[
                        "Run Playtrace on Windows or copy in a database captured from a Windows machine.",
                    ],
                )
            )

        if not self._admin_checker():
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="not-admin",
                    summary="Administrator access is disabled, so protected sources may stay blocked.",
                    remediation=[
                        "Relaunch the shell as Administrator before running `playtrace scan`.",
                    ],
                )
            )

        prefetch_status = self._path_status(r"C:\Windows\Prefetch")
        if prefetch_status != "present":
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="prefetch-unavailable",
                    summary=f"Windows Prefetch is {prefetch_status}.",
                    remediation=[
                        "Confirm Prefetch is enabled and re-run `playtrace scan`.",
                        "If access is blocked, try again from an elevated shell.",
                    ],
                )
            )

        srum_status = self._path_status(r"C:\Windows\System32\sru\SRUDB.dat")
        if srum_status != "present":
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="srum-unavailable",
                    summary=f"SRUM database access is {srum_status}.",
                    remediation=[
                        "Run elevated and close tools that may be locking `SRUDB.dat` before rescanning.",
                    ],
                )
            )

        return findings

    def _data_findings(self, db: Database) -> list[DoctorFinding]:
        findings: list[DoctorFinding] = []
        sources, evidence_types = db.load_evidence_inventory()
        snapshot = db.load_snapshot(limit=5)
        duplicate_groups = db.count_duplicate_title_groups()
        session_count = db.count_sessions()

        if not sources:
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="no-evidence",
                    summary="No evidence has been ingested into the database yet.",
                    remediation=[
                        "Run `playtrace scan` to collect a baseline dataset.",
                    ],
                )
            )

        if not {"process_start", "process_exit"} <= evidence_types:
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="exact-runtime-unavailable",
                    summary="Exact runtime evidence is incomplete, so runtime will stay inferred or unknown.",
                    remediation=[
                        "Enable Security Log process auditing and rescan.",
                        "Run `playtrace scan --source security_log --full` from an elevated shell.",
                    ],
                )
            )

        if duplicate_groups:
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="duplicate-titles",
                    summary=f"{duplicate_groups} suspected duplicate title groups were found in the database.",
                    remediation=[
                        "Review title mappings and merge duplicate titles before trusting aggregate runtime totals.",
                    ],
                )
            )

        if snapshot.coverage.unmapped_executables:
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="unmapped-executables",
                    summary=(
                        f"{snapshot.coverage.unmapped_executables} executables are still unmapped to a title."
                    ),
                    remediation=[
                        "Add or refine mappings so those executables stop surfacing as unknown titles.",
                    ],
                )
            )

        if session_count == 0:
            findings.append(
                DoctorFinding(
                    severity="warn",
                    code="missing-sessions",
                    summary="No reconstructed sessions were found in the database.",
                    remediation=[
                        "Collect more evidence and rescan after launching a title long enough to reconstruct a session.",
                    ],
                )
            )

        return findings

    def _status_for_path(self, path: str) -> str:
        try:
            return "present" if Path(path).exists() else "missing"
        except PermissionError:
            return "inaccessible"
        except OSError:
            return "missing"

    def _is_admin(self) -> bool:
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
