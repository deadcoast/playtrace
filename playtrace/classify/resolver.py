from __future__ import annotations

from collections import defaultdict
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
    normalized_title: str
    informative_tokens: tuple[str, ...]
    length_band: int
    prefix_key: str | None
    suffix_key: str | None


class TitleResolver:
    _CONFIDENCE_ORDER = {
        ConfidenceLevel.HIGH: 0,
        ConfidenceLevel.MEDIUM: 1,
        ConfidenceLevel.LOW: 2,
        ConfidenceLevel.UNKNOWN: 3,
    }
    _DUPLICATE_TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
    _DUPLICATE_TOKEN_STOPWORDS = {
        "demo",
        "edition",
        "game",
        "launcher",
        "the",
        "trial",
    }
    _DUPLICATE_HEAD_TAIL_LENGTH = 3
    _DUPLICATE_DENSE_BUCKET_LIMIT = 12

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
        candidate_pairs = self._duplicate_candidate_pairs(titles)
        fingerprints = [self._duplicate_fingerprint(index, title) for index, title in enumerate(titles)]
        verified_pairs: set[tuple[int, int]] = set()
        pair_reasons: dict[tuple[int, int], list[str]] = {}
        adjacency: dict[int, set[int]] = defaultdict(set)

        for left_index, right_index in sorted(candidate_pairs):
            duplicate_reasons = self._duplicate_reasons(titles[left_index], titles[right_index])
            if not duplicate_reasons:
                continue
            pair = (left_index, right_index)
            verified_pairs.add(pair)
            pair_reasons[pair] = duplicate_reasons
            adjacency[left_index].add(right_index)
            adjacency[right_index].add(left_index)

        candidates: list[DuplicateCandidate] = []
        remaining = set(adjacency)
        while remaining:
            component = self._duplicate_group_component(min(remaining), adjacency, remaining)
            primary_index = self._select_duplicate_primary(component, titles)
            related_indexes = sorted(
                index
                for index in adjacency.get(primary_index, set())
                if index in component and index in remaining
            )
            if not related_indexes:
                remaining.remove(primary_index)
                continue

            primary = titles[primary_index]
            related = [titles[index] for index in related_indexes]
            reasons = sorted(
                {
                    reason
                    for related_index in related_indexes
                    for reason in pair_reasons[self._ordered_pair(primary_index, related_index)]
                }
            )
            candidates.append(
                DuplicateCandidate(
                    primary_title_id=primary.title_id,
                    primary_title=primary.title,
                    related_title_ids=[title.title_id for title in related],
                    related_titles=[title.title for title in related],
                    reasons=sorted(set(reasons)),
                )
            )
            remaining.difference_update({primary_index, *related_indexes})

        return candidates

    def _duplicate_fingerprint(self, index: int, title: ResolvedTitle) -> _DuplicateFingerprint:
        normalized_title = normalize_title(title.title)
        return _DuplicateFingerprint(
            index=index,
            normalized_title=normalized_title,
            informative_tokens=self._informative_duplicate_tokens(title.title),
            length_band=len(normalized_title) // 8,
            prefix_key=self._duplicate_head_key(normalized_title),
            suffix_key=self._duplicate_tail_key(normalized_title),
        )

    def _informative_duplicate_tokens(self, title: str) -> tuple[str, ...]:
        tokens: list[str] = []
        seen: set[str] = set()

        for raw_token in self._DUPLICATE_TOKEN_PATTERN.findall(title.casefold()):
            token = normalize_title(raw_token)
            if token in seen or token in self._DUPLICATE_TOKEN_STOPWORDS:
                continue

            has_digit = any(character.isdigit() for character in token)
            if len(token) < 3 and not has_digit:
                continue
            if token.isdigit() and len(token) < 2:
                continue

            seen.add(token)
            tokens.append(token)

        if tokens:
            return tuple(tokens)

        normalized_title = normalize_title(title)
        return (normalized_title,) if normalized_title else ()

    def _duplicate_candidate_pairs(self, titles: list[ResolvedTitle]) -> set[tuple[int, int]]:
        fingerprints = [self._duplicate_fingerprint(index, title) for index, title in enumerate(titles)]
        normalized_buckets: dict[str, list[_DuplicateFingerprint]] = defaultdict(list)
        token_buckets: dict[str, list[_DuplicateFingerprint]] = defaultdict(list)
        prefix_buckets: dict[str, list[_DuplicateFingerprint]] = defaultdict(list)
        suffix_buckets: dict[str, list[_DuplicateFingerprint]] = defaultdict(list)

        for fingerprint in fingerprints:
            if fingerprint.normalized_title:
                normalized_buckets[fingerprint.normalized_title].append(fingerprint)
            for token in fingerprint.informative_tokens:
                token_buckets[token].append(fingerprint)
            if fingerprint.prefix_key:
                prefix_buckets[fingerprint.prefix_key].append(fingerprint)
            if fingerprint.suffix_key:
                suffix_buckets[fingerprint.suffix_key].append(fingerprint)

        pairs: set[tuple[int, int]] = set()
        for bucket in normalized_buckets.values():
            self._extend_duplicate_candidate_pairs(bucket, pairs, bucket_kind="normalized")
        for bucket in token_buckets.values():
            self._extend_duplicate_candidate_pairs(bucket, pairs, bucket_kind="token")
        for bucket in prefix_buckets.values():
            self._extend_duplicate_candidate_pairs(bucket, pairs, bucket_kind="prefix")
        for bucket in suffix_buckets.values():
            self._extend_duplicate_candidate_pairs(bucket, pairs, bucket_kind="suffix")
        return pairs

    def _extend_duplicate_candidate_pairs(
        self,
        bucket: list[_DuplicateFingerprint],
        pairs: set[tuple[int, int]],
        *,
        bucket_kind: str,
    ) -> None:
        dense_bucket = len(bucket) > self._DUPLICATE_DENSE_BUCKET_LIMIT
        for left_offset, left in enumerate(bucket):
            for right in bucket[left_offset + 1 :]:
                if dense_bucket and not self._keep_dense_duplicate_pair(
                    left,
                    right,
                    bucket_kind=bucket_kind,
                ):
                    continue
                pairs.add((left.index, right.index))

    def _keep_dense_duplicate_pair(
        self,
        left: _DuplicateFingerprint,
        right: _DuplicateFingerprint,
        *,
        bucket_kind: str,
    ) -> bool:
        del bucket_kind
        return (
            left.normalized_title in right.normalized_title
            or right.normalized_title in left.normalized_title
        )

    def _duplicate_group_component(
        self,
        start_index: int,
        adjacency: dict[int, set[int]],
        remaining: set[int],
    ) -> list[int]:
        stack = [start_index]
        component: list[int] = []
        visited: set[int] = set()

        while stack:
            current = stack.pop()
            if current in visited or current not in remaining:
                continue
            visited.add(current)
            component.append(current)
            stack.extend(
                neighbor
                for neighbor in sorted(adjacency.get(current, set()), reverse=True)
                if neighbor in remaining and neighbor not in visited
            )

        return sorted(component)

    def _select_duplicate_primary(
        self,
        component: list[int],
        titles: list[ResolvedTitle],
    ) -> int:
        return sorted(
            component,
            key=lambda index: (
                self._CONFIDENCE_ORDER.get(titles[index].title_confidence, 99),
                -len(normalize_title(titles[index].title)),
                titles[index].title.casefold(),
            ),
        )[0]

    def _ordered_pair(self, left_index: int, right_index: int) -> tuple[int, int]:
        return (left_index, right_index) if left_index < right_index else (right_index, left_index)

    def _duplicate_head_key(self, normalized_title: str) -> str | None:
        if len(normalized_title) < self._DUPLICATE_HEAD_TAIL_LENGTH:
            return normalized_title or None
        return normalized_title[: self._DUPLICATE_HEAD_TAIL_LENGTH]

    def _duplicate_tail_key(self, normalized_title: str) -> str | None:
        if len(normalized_title) < self._DUPLICATE_HEAD_TAIL_LENGTH:
            return normalized_title or None
        return normalized_title[-self._DUPLICATE_HEAD_TAIL_LENGTH :]

    def _duplicate_reasons(self, left: ResolvedTitle, right: ResolvedTitle) -> list[str]:
        normalized_left = normalize_title(left.title)
        normalized_right = normalize_title(right.title)
        if not normalized_left or not normalized_right:
            return []

        anchor_reasons: list[str] = []
        supporting_reasons: list[str] = []
        if normalized_left == normalized_right:
            anchor_reasons.extend(
                [
                    "metadata-backed title similarity",
                    "normalized title collision",
                ]
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
