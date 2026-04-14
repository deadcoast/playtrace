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


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"