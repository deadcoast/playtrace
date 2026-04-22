from __future__ import annotations

from playtrace.models.enums import Classification, ConfidenceLevel
from playtrace.models.executable import ExecutableIdentity

LAUNCHER_TOKENS = {
    "steam.exe": "Steam",
    "epicgameslauncher.exe": "Epic Games",
    "galaxyclient.exe": "GOG Galaxy",
    "battle.net.exe": "Battle.net",
    "eadesktop.exe": "EA App",
    "upc.exe": "Ubisoft Connect",
}

HELPER_TOKENS = {
    "crashreporter": "crash_reporter",
    "crash reporter": "crash_reporter",
    "start_protected_game": "anti_cheat",
    "easy anti-cheat": "anti_cheat",
    "easyanticheat": "anti_cheat",
    "updater": "updater",
    "bootstrap": "bootstrap",
    "helper": "helper",
}


def classify_executable(
    executable: ExecutableIdentity,
) -> tuple[Classification, str | None, ConfidenceLevel]:
    haystack = " ".join(
        part.lower()
        for part in [
            executable.filename or "",
            executable.path or "",
            executable.product_name or "",
            executable.file_description or "",
        ]
        if part
    )

    if executable.path and executable.path.lower().startswith("c:\\windows\\"):
        return Classification.SYSTEM, None, ConfidenceLevel.HIGH

    for token in LAUNCHER_TOKENS:
        if token in haystack:
            return Classification.LAUNCHER, None, ConfidenceLevel.HIGH

    for token, subtype in HELPER_TOKENS.items():
        if token in haystack:
            return Classification.HELPER, subtype, ConfidenceLevel.HIGH

    if "overlay" in haystack:
        return Classification.OVERLAY, "overlay", ConfidenceLevel.MEDIUM

    return Classification.UNKNOWN, None, ConfidenceLevel.UNKNOWN


def infer_launcher_name(executable: ExecutableIdentity) -> str | None:
    haystack = " ".join(
        part.lower()
        for part in [
            executable.filename or "",
            executable.path or "",
            executable.product_name or "",
        ]
        if part
    )
    for token, label in LAUNCHER_TOKENS.items():
        if token in haystack:
            return label
    return None
