from __future__ import annotations

from difflib import SequenceMatcher
import re

from playtrace.models.enums import Classification
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.session import SessionRecord


def total_runtime_by_executable(sessions: list[SessionRecord]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for session in sessions:
        totals[session.exe_id] = totals.get(session.exe_id, 0) + int(session.duration_seconds or 0)
    return totals


def normalize_title(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def title_similarity(left: str, right: str) -> float:
    normalized_left = normalize_title(left)
    normalized_right = normalize_title(right)
    if not normalized_left or not normalized_right:
        return 0.0
    if normalized_left == normalized_right:
        return 1.0
    if normalized_left in normalized_right or normalized_right in normalized_left:
        return min(len(normalized_left), len(normalized_right)) / max(len(normalized_left), len(normalized_right))
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def executable_identity_score(
    executable: ExecutableIdentity,
    sessions: list[SessionRecord],
) -> int:
    runtime_totals = total_runtime_by_executable(sessions)
    score = runtime_totals.get(executable.exe_id, 0)

    if executable.classification == Classification.GAME:
        score += 1_000_000
    elif executable.classification in {
        Classification.LAUNCHER,
        Classification.HELPER,
        Classification.RUNTIME,
        Classification.SYSTEM,
        Classification.OVERLAY,
    }:
        score -= 1_000_000

    if executable.product_name:
        score += 50_000
    if executable.original_filename:
        score += 10_000
    if executable.sha1:
        score += 10_000
    if executable.signer:
        score += 5_000
    if executable.canonical_path:
        score += 2_500

    return score


def choose_primary_executable(
    executables: list[ExecutableIdentity],
    sessions: list[SessionRecord],
) -> ExecutableIdentity | None:
    best: ExecutableIdentity | None = None
    best_score = -1

    for executable in executables:
        if executable.ignored:
            continue

        score = executable_identity_score(executable, sessions)
        if score > best_score:
            best = executable
            best_score = score

    return best
