from __future__ import annotations

from enum import Enum


class EvidenceStrength(str, Enum):
    EXACT = "exact"
    STRONG = "strong"
    INTERACTIVE = "interactive"
    ESTIMATED = "estimated"
    WEAK = "weak"
    UNKNOWN = "unknown"


class Classification(str, Enum):
    GAME = "game"
    LAUNCHER = "launcher"
    HELPER = "helper"
    RUNTIME = "runtime"
    OVERLAY = "overlay"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class SourceName(str, Enum):
    SECURITY_LOG = "security_log"
    PREFETCH = "prefetch"
    USERASSIST = "userassist"
    SRUM = "srum"
    AMCACHE = "amcache"
    BAM = "bam"


class EvidenceType(str, Enum):
    PROCESS_START = "process_start"
    PROCESS_EXIT = "process_exit"
    EXECUTION_COUNT = "execution_count"
    RECENT_EXECUTION = "recent_execution"
    INTERACTIVE_LAUNCH = "interactive_launch"
    FOREGROUND_USAGE = "foreground_usage"
    ACTIVITY_WINDOW = "activity_window"
    IDENTITY = "identity"


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class RuntimeConfidence(str, Enum):
    EXACT = "exact"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"
