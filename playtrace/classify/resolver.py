from __future__ import annotations

from dataclasses import dataclass, field

from playtrace.classify.heuristics import choose_primary_executable
from playtrace.classify.rules import classify_executable, infer_launcher_name
from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.session import SessionRecord


@dataclass(slots=True)
class ResolvedTitle:
    title_id: str
    title: str
    classification: Classification
    classification_confidence: ConfidenceLevel
    title_confidence: ConfidenceLevel
    launcher: str | None
    primary_exe_id: str | None
    executable_ids: list[str] = field(default_factory=list)
    suppressed_executable_ids: list[str] = field(default_factory=list)


class TitleResolver:
    def resolve(
        self,
        executables: list[ExecutableIdentity],
        sessions: list[SessionRecord],
        mappings: list[UserMapping] | None = None,
    ) -> list[ResolvedTitle]:
        mappings = mappings or []
        mapping_by_target = {mapping.target: mapping for mapping in mappings if not mapping.ignore}

        classified: list[ExecutableIdentity] = []
        for executable in executables:
            mapping = mapping_by_target.get(executable.exe_id)
            classification, subtype, confidence = classify_executable(executable)
            classified.append(
                ExecutableIdentity(
                    exe_id=executable.exe_id,
                    normalized_key=executable.normalized_key,
                    path=executable.path,
                    filename=executable.filename,
                    original_filename=executable.original_filename,
                    product_name=executable.product_name,
                    file_description=executable.file_description,
                    signer=executable.signer,
                    company_name=executable.company_name,
                    sha1=executable.sha1,
                    canonical_path=executable.canonical_path,
                    classification=mapping.classification if mapping and mapping.classification else classification,
                    classification_subtype=subtype,
                    classification_confidence=confidence,
                    ignored=executable.ignored or (mapping.ignore if mapping else False),
                    first_seen=executable.first_seen,
                    last_seen=executable.last_seen,
                    aliases=set(executable.aliases),
                    tags=set(executable.tags),
                )
            )

        active = [executable for executable in classified if not executable.ignored]
        if not active:
            return []

        primary = choose_primary_executable(active, sessions) or active[0]
        primary_mapping = mapping_by_target.get(primary.exe_id)
        title = primary_mapping.title if primary_mapping else self._title_from_executable(primary)
        title_confidence = ConfidenceLevel.HIGH if primary_mapping else (
            ConfidenceLevel.HIGH if primary.product_name else ConfidenceLevel.MEDIUM
        )
        launcher = primary_mapping.launcher if primary_mapping else self._launcher_name(active)

        suppressed = [
            executable.exe_id
            for executable in active
            if executable.exe_id != primary.exe_id
            and executable.classification in {Classification.LAUNCHER, Classification.HELPER, Classification.RUNTIME}
        ]

        return [
            ResolvedTitle(
                title_id=self._title_id(title),
                title=title,
                classification=primary.classification,
                classification_confidence=primary.classification_confidence,
                title_confidence=title_confidence,
                launcher=launcher,
                primary_exe_id=primary.exe_id,
                executable_ids=[primary.exe_id],
                suppressed_executable_ids=suppressed,
            )
        ]

    def _title_from_executable(self, executable: ExecutableIdentity) -> str:
        if executable.product_name:
            return executable.product_name
        if executable.filename:
            return executable.filename.rsplit(".", 1)[0]
        return executable.exe_id

    def _launcher_name(self, executables: list[ExecutableIdentity]) -> str | None:
        for executable in executables:
            name = infer_launcher_name(executable)
            if name:
                return name
        return None

    def _title_id(self, title: str) -> str:
        normalized = "_".join(title.lower().split())
        return f"title:{normalized}"
