from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from playtrace.config.loader import ConfigLoader
from playtrace.config.resolver import ConfigResolver
from playtrace.config.runtime import RawExportInput, UNSET
from playtrace.services.lineage import LineageService
from playtrace.services.rebuild import RebuildService
from playtrace.store.db import Database
from playtrace.utils.clock import Clock


@dataclass(slots=True, init=False)
class ExportRequest:
    db_path: Path
    output_path: Path
    config_path: Path | None
    spec_name: str | None
    raw: RawExportInput

    def __init__(
        self,
        *,
        db_path: Path,
        output_path: Path,
        config_path: Path | None = None,
        spec_name: str | None = None,
        raw: RawExportInput | None = None,
        format: str | None = None,
        scope: str | None = None,
    ) -> None:
        self.db_path = db_path
        self.output_path = output_path
        self.config_path = config_path
        self.spec_name = spec_name
        self.raw = raw or RawExportInput(
            format=format if format is not None else UNSET,
            scope=scope if scope is not None else UNSET,
        )


class ExporterService:
    def __init__(
        self,
        *,
        config_loader: ConfigLoader | None = None,
        resolver: ConfigResolver | None = None,
        lineage_service: LineageService | None = None,
        rebuild_service: RebuildService | None = None,
    ) -> None:
        self.config_loader = config_loader or ConfigLoader()
        self.resolver = resolver or ConfigResolver()
        self.lineage_service = lineage_service or LineageService()
        self.rebuild_service = rebuild_service or RebuildService()

    def run(self, request: ExportRequest) -> None:
        db = Database(request.db_path)
        db.bootstrap()
        snapshot = db.load_snapshot(limit=250)
        resolved = self._resolve(request)
        format_name = (resolved.format or "json").lower()
        scope_name = (resolved.scope or "entity").lower()

        if format_name == "json":
            payload = self._build_json_payload(
                db=db,
                snapshot=snapshot,
                scope_name=scope_name,
                request=request,
                resolved=resolved,
            )
            request.output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            return

        if scope_name != "entity":
            raise ValueError(f"Scope {scope_name} requires --format json.")

        if format_name == "csv":
            self._write_csv(request.output_path, snapshot.top_titles)
            return

        if format_name == "markdown":
            request.output_path.write_text(self._build_markdown(snapshot), encoding="utf-8")
            return

        raise ValueError(f"Unsupported export format: {resolved.format}")

    def _resolve(self, request: ExportRequest):
        config = self.config_loader.load(request.config_path)
        return self.resolver.resolve_export(
            config=config,
            cli=request.raw,
            spec_name=request.spec_name,
        )

    def _build_json_payload(
        self,
        *,
        db: Database,
        snapshot,
        scope_name: str,
        request: ExportRequest,
        resolved,
    ) -> dict[str, object]:
        if scope_name == "entity":
            return self._build_entity_payload(
                snapshot=snapshot,
                sessions=db.load_sessions(title=None, days=3650, limit=1000),
            )
        if scope_name == "lineage":
            return self._build_lineage_payload(db=db, snapshot=snapshot, request=request)
        if scope_name == "repair-preview":
            return self._build_repair_preview_payload(snapshot=snapshot, request=request, resolved=resolved)
        raise ValueError(f"Unsupported export scope: {scope_name}")

    def _build_entity_payload(self, *, snapshot, sessions) -> dict[str, object]:
        return {
            "scope": "entity",
            "generated_at": Clock.format_iso8601(snapshot.generated_at),
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
                    "launches_gui": title.launches.gui,
                }
                for title in snapshot.top_titles
            ],
            "sessions": [
                {
                    "title": title,
                    "session_id": session.session_id,
                    "title_id": session.title_id,
                    "exe_id": session.exe_id,
                    "started_at": Clock.format_iso8601(session.started_at),
                    "ended_at": Clock.format_iso8601(session.ended_at),
                    "duration_seconds": session.duration_seconds,
                    "confidence": session.confidence.value,
                }
                for title, session in sessions
            ],
            "warnings": snapshot.warnings,
        }

    def _build_lineage_payload(self, *, db: Database, snapshot, request: ExportRequest) -> dict[str, object]:
        titles = db.load_titles(
            sort_by="runtime",
            classification=None,
            launcher=None,
            limit=10_000,
        )
        duplicates = db.load_duplicate_candidates()
        return {
            "scope": "lineage",
            "generated_at": Clock.format_iso8601(snapshot.generated_at),
            "host_name": snapshot.host_name,
            "entities": [
                self._serialize_entity_lineage(
                    self.lineage_service.load_entity(request.db_path, title.title)
                )
                for title in titles
            ],
            "duplicates": [
                {
                    "primary_title_id": candidate.primary_title_id,
                    "primary_title": candidate.primary_title,
                    "related_title_ids": candidate.related_title_ids,
                    "related_titles": candidate.related_titles,
                    "reasons": candidate.reasons,
                }
                for candidate in duplicates
            ],
            "warnings": snapshot.warnings,
        }

    def _build_repair_preview_payload(self, *, snapshot, request: ExportRequest, resolved) -> dict[str, object]:
        preview = self.rebuild_service.plan(
            request.db_path,
            settings=resolved.reconstruction,
        )
        return {
            "scope": "repair-preview",
            "generated_at": Clock.format_iso8601(snapshot.generated_at),
            "host_name": snapshot.host_name,
            "repair": {
                "counts": {
                    "merged_titles": preview.counts.merged_titles,
                    "changed_titles": preview.counts.changed_titles,
                    "changed_sessions": preview.counts.changed_sessions,
                    "remaining_duplicate_groups": preview.counts.remaining_duplicate_groups,
                },
                "title_changes": preview.title_changes,
                "session_changes": preview.session_changes,
                "unresolved": preview.unresolved,
            },
            "warnings": snapshot.warnings,
        }

    def _serialize_entity_lineage(self, snapshot) -> dict[str, object]:
        return {
            "title": snapshot.title,
            "runtime_confidence": snapshot.runtime_confidence,
            "confidence_reasons": snapshot.confidence_reasons,
            "alternate_titles": snapshot.alternate_titles,
            "conflicts": snapshot.conflicts,
            "contributions": [
                {
                    "source": contribution.source,
                    "evidence_type": contribution.evidence_type,
                    "strength": contribution.strength,
                    "observed_at": contribution.observed_at,
                    "evidence_id": contribution.evidence_id,
                    "raw_ref": contribution.raw_ref,
                    "title_hint": contribution.title_hint,
                    "reasoning": contribution.reasoning,
                }
                for contribution in snapshot.contributions
            ],
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
                    "launches_gui",
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
                        title.launches.gui,
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
                f"{title.launches.confirmed + title.launches.inferred + title.launches.gui} launches"
            )
        return "\n".join(lines) + "\n"
