from __future__ import annotations

from playtrace.models.enums import Classification
from playtrace.models.executable import ExecutableIdentity
from playtrace.models.session import SessionRecord


def total_runtime_by_executable(sessions: list[SessionRecord]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for session in sessions:
        totals[session.exe_id] = totals.get(session.exe_id, 0) + int(session.duration_seconds or 0)
    return totals


def choose_primary_executable(
    executables: list[ExecutableIdentity],
    sessions: list[SessionRecord],
) -> ExecutableIdentity | None:
    runtime_totals = total_runtime_by_executable(sessions)
    best: ExecutableIdentity | None = None
    best_score = -1

    for executable in executables:
        if executable.ignored:
            continue

        score = runtime_totals.get(executable.exe_id, 0)
        if executable.classification == Classification.GAME:
            score += 1_000_000
        elif executable.classification in {
            Classification.LAUNCHER,
            Classification.HELPER,
            Classification.RUNTIME,
            Classification.SYSTEM,
        }:
            score -= 1_000_000

        if score > best_score:
            best = executable
            best_score = score

    return best
