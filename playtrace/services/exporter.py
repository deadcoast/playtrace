from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from playtrace.store.db import Database


@dataclass(slots=True)
class ExportRequest:
    db_path: Path
    output_path: Path
    format: str


class ExporterService:
    def run(self, request: ExportRequest) -> None:
        db = Database(request.db_path)
        db.bootstrap()
        snapshot = db.load_snapshot(limit=250)
        format_name = request.format.lower()

        if format_name == "json":
            payload = self._build_export_payload(db)
            request.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return

        if format_name == "csv":
            self._write_csv(request.output_path, snapshot.top_titles)
            return

        if format_name == "markdown":
            request.output_path.write_text(self._build_markdown(snapshot), encoding="utf-8")
            return

        raise ValueError(f"Unsupported export format: {request.format}")

    def _build_export_payload(self, db: Database) -> dict[str, object]:
        snapshot = db.load_snapshot(limit=250)
        sessions = db.load_sessions(title=None, days=3650, limit=1000)
        return {
            "generated_at": snapshot.generated_at.isoformat(),
            "host_name": snapshot.host_name,
            "coverage": {
                "tracked_titles": snapshot.coverage.tracked_titles,
                "confirmed_runtime_seconds": snapshot.coverage.confirmed_runtime_seconds,
                "estimated_runtime_seconds": snapshot.coverage.estimated_runtime_seconds,
                "confirmed_sessions": snapshot.coverage.confirmed_sessions,
                "unmapped_executables": snapshot.coverage.unmapped_executables,
            },
            "titles": [
                {
                    "title_id": title.title_id,
                    "title": title.title,
                    "classification": title.classification.value,
                    "launcher": title.launcher,
                    "confirmed_seconds": title.runtime.confirmed_seconds,
                    "estimated_seconds": title.runtime.estimated_seconds,
                    "launches_confirmed": title.launches.confirmed,
                    "launches_inferred": title.launches.inferred,
                }
                for title in snapshot.top_titles
            ],
            "sessions": [
                {
                    "title": title,
                    "session_id": session.session_id,
                    "title_id": session.title_id,
                    "exe_id": session.exe_id,
                    "started_at": session.started_at.isoformat() if session.started_at else None,
                    "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                    "duration_seconds": session.duration_seconds,
                    "confidence": session.confidence.value,
                }
                for title, session in sessions
            ],
            "warnings": snapshot.warnings,
        }

    def _write_csv(self, output_path: Path, titles) -> None:
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "title_id",
                    "title",
                    "classification",
                    "launcher",
                    "confirmed_seconds",
                    "estimated_seconds",
                    "launches_confirmed",
                    "launches_inferred",
                ]
            )
            for title in titles:
                writer.writerow(
                    [
                        title.title_id,
                        title.title,
                        title.classification.value,
                        title.launcher or "",
                        title.runtime.confirmed_seconds,
                        title.runtime.estimated_seconds,
                        title.launches.confirmed,
                        title.launches.inferred,
                    ]
                )

    def _build_markdown(self, snapshot) -> str:
        lines = [
            "# playtrace export",
            "",
            f"- Host: {snapshot.host_name}",
            f"- Tracked titles: {snapshot.coverage.tracked_titles}",
            f"- Confirmed sessions: {snapshot.coverage.confirmed_sessions}",
            "",
            "## Top titles",
            "",
        ]
        for title in snapshot.top_titles:
            lines.append(
                f"- {title.title}: {title.runtime.confirmed_seconds}s confirmed, "
                f"{title.launches.confirmed + title.launches.inferred} launches"
            )
        return "\n".join(lines) + "\n"
