from __future__ import annotations

from dataclasses import dataclass, field
import re

from playtrace.classify.heuristics import choose_primary_executable
from playtrace.classify.rules import classify_executable, infer_launcher_name
from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.mapping import UserMapping
from playtrace.models.report import DuplicateCandidate
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


@dataclass(slots=True)
class ResolveResult:
    titles: list[ResolvedTitle]
    duplicate_candidates: list[DuplicateCandidate] = field(default_factory=list)


class TitleResolver:
    def resolve(
        self,
        executables: list[ExecutableIdentity],
        sessions: list[SessionRecord],
        mappings: list[UserMapping] | None = None,
    ) -> ResolveResult:
        mappings = mappings or []
        mapping_by_target = self._mapping_lookup(mappings)

        classified: list[ExecutableIdentity] = []
        for executable in executables:
            mapping = self._mapping_for_executable(executable, mapping_by_target)
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
            return ResolveResult(titles=[])

        groups = self._group_active_executables(active, sessions, mapping_by_target)
        grouped_count = len(groups)

        resolved: list[ResolvedTitle] = []
        for group in groups:
            primary = choose_primary_executable(group, sessions) or group[0]
            primary_mapping = self._mapping_for_executable(primary, mapping_by_target)
            title = primary_mapping.title if primary_mapping else self._title_from_executable(primary)
            title_confidence = ConfidenceLevel.HIGH if primary_mapping else (
                ConfidenceLevel.HIGH if primary.product_name else ConfidenceLevel.MEDIUM
            )
            classification_confidence = (
                ConfidenceLevel.HIGH
                if primary_mapping and primary_mapping.classification
                else primary.classification_confidence
            )
            launcher_source = active if grouped_count == 1 else group
            launcher = (
                primary_mapping.launcher
                if primary_mapping and primary_mapping.launcher
                else self._launcher_name(launcher_source)
            )
            executable_ids = [executable.exe_id for executable in group]
            suppressed = (
                [
                    executable.exe_id
                    for executable in active
                    if executable.exe_id not in executable_ids
                    and executable.classification in self._suppressed_classifications()
                ]
                if grouped_count == 1
                else []
            )

            resolved.append(
                ResolvedTitle(
                    title_id=self._title_id(title),
                    title=title,
                    classification=primary.classification,
                    classification_confidence=classification_confidence,
                    title_confidence=title_confidence,
                    launcher=launcher,
                    primary_exe_id=primary.exe_id,
                    executable_ids=executable_ids,
                    suppressed_executable_ids=suppressed,
                )
            )

        return ResolveResult(
            titles=resolved,
            duplicate_candidates=self._duplicate_candidates(resolved),
        )

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

    def _mapping_lookup(self, mappings: list[UserMapping]) -> dict[str, UserMapping]:
        lookup: dict[str, UserMapping] = {}
        for mapping in mappings:
            lookup[mapping.target] = mapping
            if mapping.normalized_key:
                lookup[mapping.normalized_key] = mapping
        return lookup

    def _mapping_for_executable(
        self,
        executable: ExecutableIdentity,
        mapping_by_target: dict[str, UserMapping],
    ) -> UserMapping | None:
        return (
            mapping_by_target.get(executable.exe_id)
            or mapping_by_target.get(executable.normalized_key)
        )

    def _group_active_executables(
        self,
        executables: list[ExecutableIdentity],
        sessions: list[SessionRecord],
        mapping_by_target: dict[str, UserMapping],
    ) -> list[list[ExecutableIdentity]]:
        title_groups: dict[str, list[ExecutableIdentity]] = {}

        for executable in executables:
            mapping = self._mapping_for_executable(executable, mapping_by_target)
            if not self._is_title_candidate(executable, mapping):
                continue
            title = mapping.title if mapping else self._title_from_executable(executable)
            title_groups.setdefault(title.casefold(), []).append(executable)

        groups = list(title_groups.values())
        if groups:
            return groups

        primary = choose_primary_executable(executables, sessions) or executables[0]
        return [[primary]]

    def _is_title_candidate(
        self,
        executable: ExecutableIdentity,
        mapping: UserMapping | None,
    ) -> bool:
        if mapping and mapping.title:
            return True
        return executable.classification not in self._suppressed_classifications()

    def _suppressed_classifications(self) -> set[Classification]:
        return {
            Classification.LAUNCHER,
            Classification.HELPER,
            Classification.RUNTIME,
            Classification.OVERLAY,
            Classification.SYSTEM,
        }

    def _duplicate_candidates(self, titles: list[ResolvedTitle]) -> list[DuplicateCandidate]:
        groups: dict[str, list[ResolvedTitle]] = {}
        for title in titles:
            normalized = re.sub(r"[^a-z0-9]+", "", title.title.casefold())
            if not normalized:
                continue
            groups.setdefault(normalized, []).append(title)

        candidates: list[DuplicateCandidate] = []
        for group in groups.values():
            if len(group) < 2:
                continue
            primary = sorted(group, key=lambda item: (item.title_confidence.value, item.title.casefold()))[0]
            related = [title for title in group if title.title_id != primary.title_id]
            candidates.append(
                DuplicateCandidate(
                    primary_title_id=primary.title_id,
                    primary_title=primary.title,
                    related_title_ids=[title.title_id for title in related],
                    related_titles=[title.title for title in related],
                    reasons=["normalized title collision"],
                )
            )

        return candidates
