from __future__ import annotations

from dataclasses import dataclass, field
import re

from playtrace.classify.heuristics import choose_primary_executable, normalize_title, title_similarity
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
    alternate_titles: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    executable_ids: list[str] = field(default_factory=list)
    suppressed_executable_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ResolveResult:
    titles: list[ResolvedTitle]
    duplicate_candidates: list[DuplicateCandidate] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class _DuplicateFingerprint:
    index: int
    title_id: str
    normalized_title: str
    informative_tokens: tuple[str, ...]
    length_band: int
    launcher_key: str | None


class TitleResolver:
    _CONFIDENCE_ORDER = {
        ConfidenceLevel.HIGH: 0,
        ConfidenceLevel.MEDIUM: 1,
        ConfidenceLevel.LOW: 2,
        ConfidenceLevel.UNKNOWN: 3,
    }
    _DUPLICATE_TOKEN_STOPWORDS = {
        "app",
        "edition",
        "game",
        "games",
        "launcher",
        "runtime",
        "service",
        "setup",
        "steam",
        "system",
        "update",
    }

    def resolve(
        self,
        executables: list[ExecutableIdentity],
        sessions: list[SessionRecord],
        mappings: list[UserMapping] | None = None,
        config_overrides: dict[str, str] | None = None,
    ) -> ResolveResult:
        mappings = mappings or []
        mapping_by_target = self._mapping_lookup(mappings)
        config_override_lookup = self._config_override_lookup(config_overrides or {})

        classified: list[ExecutableIdentity] = []
        for executable in executables:
            mapping = self._mapping_for_executable(executable, mapping_by_target)
            override_classification = self._config_override_for_executable(
                executable,
                config_override_lookup,
            )
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
                    classification=(
                        mapping.classification
                        if mapping and mapping.classification
                        else override_classification or classification
                    ),
                    classification_subtype=subtype,
                    classification_confidence=(
                        ConfidenceLevel.HIGH if override_classification else confidence
                    ),
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
            observed_titles = self._observed_titles(group, primary_mapping)
            title = (
                primary_mapping.title
                if primary_mapping and primary_mapping.title
                else self._canonical_group_title(primary, observed_titles)
            )
            title_confidence = (
                ConfidenceLevel.HIGH
                if primary_mapping and primary_mapping.title
                else self._title_confidence(primary, observed_titles)
            )
            notes = self._title_notes(primary, primary_mapping, observed_titles, title_confidence)
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
                    alternate_titles=[
                        candidate
                        for candidate in observed_titles
                        if candidate.casefold() != title.casefold()
                    ],
                    notes=notes,
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

    def _observed_titles(
        self,
        executables: list[ExecutableIdentity],
        mapping: UserMapping | None,
    ) -> list[str]:
        candidates: list[str] = []
        if mapping and mapping.title:
            candidates.append(mapping.title)
        for executable in executables:
            for candidate in [
                executable.product_name,
                executable.file_description,
                executable.original_filename.rsplit(".", 1)[0] if executable.original_filename else None,
                executable.filename.rsplit(".", 1)[0] if executable.filename else None,
            ]:
                if not candidate:
                    continue
                text = str(candidate).strip()
                if text and text not in candidates:
                    candidates.append(text)
        return candidates

    def _canonical_group_title(
        self,
        primary: ExecutableIdentity,
        observed_titles: list[str],
    ) -> str:
        if primary.product_name:
            return primary.product_name
        if observed_titles:
            return sorted(
                observed_titles,
                key=lambda item: (
                    normalize_title(item) != normalize_title(primary.product_name or item),
                    len(normalize_title(item)),
                    item.casefold(),
                ),
            )[0]
        return self._title_from_executable(primary)

    def _title_confidence(
        self,
        primary: ExecutableIdentity,
        observed_titles: list[str],
    ) -> ConfidenceLevel:
        if primary.product_name:
            return ConfidenceLevel.HIGH
        if len(observed_titles) > 1:
            return ConfidenceLevel.LOW
        return ConfidenceLevel.UNKNOWN

    def _title_notes(
        self,
        primary: ExecutableIdentity,
        mapping: UserMapping | None,
        observed_titles: list[str],
        confidence: ConfidenceLevel,
    ) -> list[str]:
        notes: list[str] = []
        if mapping and mapping.title:
            notes.append("Resolved from an explicit title override.")
            return notes
        if confidence is ConfidenceLevel.UNKNOWN:
            notes.append("Ambiguous title because metadata is too weak to select a canonical label confidently.")
        elif len(observed_titles) > 1:
            notes.append("Multiple observed labels were collapsed into one canonical title.")
        if primary.classification in self._suppressed_classifications():
            notes.append("Primary executable is normally suppressed, so this title remains provisional.")
        return notes

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

    def _config_override_lookup(self, config_overrides: dict[str, str]) -> dict[str, Classification]:
        lookup: dict[str, Classification] = {}
        for target, classification_name in config_overrides.items():
            try:
                classification = Classification(classification_name)
            except ValueError:
                continue
            keys = {
                target,
                target.casefold(),
                target.replace("/", "\\"),
                target.replace("/", "\\").casefold(),
            }
            for key in keys:
                lookup[key] = classification
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

    def _config_override_for_executable(
        self,
        executable: ExecutableIdentity,
        override_lookup: dict[str, Classification],
    ) -> Classification | None:
        candidates = [
            executable.exe_id,
            executable.normalized_key,
            executable.path,
        ]
        for candidate in candidates:
            if not candidate:
                continue
            for key in {
                candidate,
                candidate.casefold(),
                candidate.replace("/", "\\"),
                candidate.replace("/", "\\").casefold(),
            }:
                classification = override_lookup.get(key)
                if classification is not None:
                    return classification
        return None

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
            title = mapping.title if mapping and mapping.title else self._title_from_executable(executable)
            key = normalize_title(title)
            title_groups.setdefault(key or title.casefold(), []).append(executable)

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
        verified_pairs: dict[tuple[int, int], list[str]] = {}
        for left_index, right_index in sorted(self._duplicate_candidate_pairs(titles)):
            reasons = self._duplicate_reasons(titles[left_index], titles[right_index])
            if reasons:
                verified_pairs[(left_index, right_index)] = reasons
        if not verified_pairs:
            return []

        candidates: list[DuplicateCandidate] = []
        for group_indexes in self._duplicate_groups(titles, set(verified_pairs)):
            group = [titles[index] for index in group_indexes]
            reasons = self._group_duplicate_reasons(group_indexes, verified_pairs)
            primary = sorted(
                group,
                key=lambda item: (
                    self._CONFIDENCE_ORDER.get(item.title_confidence, 99),
                    -len(normalize_title(item.title)),
                    item.title.casefold(),
                ),
            )[0]
            related = [title for title in group if title.title_id != primary.title_id]
            candidates.append(
                DuplicateCandidate(
                    primary_title_id=primary.title_id,
                    primary_title=primary.title,
                    related_title_ids=[title.title_id for title in related],
                    related_titles=[title.title for title in related],
                    reasons=reasons,
                )
            )

        return candidates

    def _duplicate_fingerprint(self, index: int, title: ResolvedTitle) -> _DuplicateFingerprint:
        normalized_title = normalize_title(title.title)
        return _DuplicateFingerprint(
            index=index,
            title_id=title.title_id,
            normalized_title=normalized_title,
            informative_tokens=self._informative_duplicate_tokens(title.title),
            length_band=max(1, len(normalized_title) // 4) if normalized_title else 0,
            launcher_key=normalize_title(title.launcher) or None,
        )

    def _informative_duplicate_tokens(self, title: str) -> tuple[str, ...]:
        tokens: list[str] = []
        for raw_token in re.findall(r"[a-z0-9]+", title.casefold()):
            token = normalize_title(raw_token)
            if len(token) < 4 or token in self._DUPLICATE_TOKEN_STOPWORDS:
                continue
            if token not in tokens:
                tokens.append(token)
        if tokens:
            return tuple(tokens)

        normalized_title = normalize_title(title)
        if len(normalized_title) >= 4:
            return (normalized_title,)
        return ()

    def _duplicate_candidate_pairs(
        self,
        titles: list[ResolvedTitle],
    ) -> set[tuple[int, int]]:
        fingerprints = [
            self._duplicate_fingerprint(index, title)
            for index, title in enumerate(titles)
        ]
        exact_buckets: dict[str, list[int]] = {}
        token_buckets: dict[str, list[int]] = {}
        for fingerprint in fingerprints:
            if fingerprint.normalized_title:
                exact_buckets.setdefault(fingerprint.normalized_title, []).append(fingerprint.index)
            for token in fingerprint.informative_tokens:
                token_buckets.setdefault(token, []).append(fingerprint.index)

        pairs: set[tuple[int, int]] = set()
        for indexes in exact_buckets.values():
            self._add_duplicate_pairs(
                indexes,
                fingerprints,
                pairs,
                exact_match=True,
            )
        for indexes in token_buckets.values():
            self._add_duplicate_pairs(indexes, fingerprints, pairs)
        return pairs

    def _add_duplicate_pairs(
        self,
        indexes: list[int],
        fingerprints: list[_DuplicateFingerprint],
        pairs: set[tuple[int, int]],
        *,
        exact_match: bool = False,
    ) -> None:
        unique_indexes = sorted(set(indexes))
        if len(unique_indexes) < 2:
            return
        if exact_match:
            anchor = unique_indexes[0]
            for other in unique_indexes[1:]:
                pairs.add((anchor, other))
            return

        sorted_indexes = sorted(
            unique_indexes,
            key=lambda index: (fingerprints[index].length_band, index),
        )
        for position, left_index in enumerate(sorted_indexes):
            left_fingerprint = fingerprints[left_index]
            for right_index in sorted_indexes[position + 1 :]:
                right_fingerprint = fingerprints[right_index]
                if right_fingerprint.length_band - left_fingerprint.length_band > 2:
                    break
                pairs.add((left_index, right_index))

    def _duplicate_groups(
        self,
        titles: list[ResolvedTitle],
        verified_pairs: set[tuple[int, int]],
    ) -> list[list[int]]:
        adjacency: dict[int, set[int]] = {}
        for left_index, right_index in verified_pairs:
            adjacency.setdefault(left_index, set()).add(right_index)
            adjacency.setdefault(right_index, set()).add(left_index)

        groups: list[list[int]] = []
        seen: set[int] = set()
        for index in range(len(titles)):
            if index in seen or index not in adjacency:
                continue
            stack = [index]
            component: list[int] = []
            while stack:
                current = stack.pop()
                if current in seen:
                    continue
                seen.add(current)
                component.append(current)
                stack.extend(sorted(adjacency[current], reverse=True))
            groups.append(sorted(component))
        return groups

    def _group_duplicate_reasons(
        self,
        group_indexes: list[int],
        verified_pairs: dict[tuple[int, int], list[str]],
    ) -> list[str]:
        indexes = set(group_indexes)
        reasons: set[str] = set()
        for (left_index, right_index), pair_reasons in verified_pairs.items():
            if left_index in indexes and right_index in indexes:
                reasons.update(pair_reasons)
        return sorted(reasons)

    def _duplicate_reasons(self, left: ResolvedTitle, right: ResolvedTitle) -> list[str]:
        anchor_reasons: list[str] = []
        supporting_reasons: list[str] = []
        normalized_left = normalize_title(left.title)
        normalized_right = normalize_title(right.title)
        if not normalized_left or not normalized_right:
            return []
        if normalized_left == normalized_right:
            anchor_reasons.extend(
                ["normalized title collision", "metadata-backed title similarity"]
            )
        elif normalized_left in normalized_right or normalized_right in normalized_left:
            anchor_reasons.append("metadata-backed title similarity")
        elif title_similarity(left.title, right.title) >= 0.70:
            anchor_reasons.append("metadata-backed title similarity")
        if left.launcher and right.launcher and left.launcher == right.launcher:
            supporting_reasons.append("shared launcher ancestry")
        if not anchor_reasons:
            return []
        return sorted(set(anchor_reasons + supporting_reasons))
