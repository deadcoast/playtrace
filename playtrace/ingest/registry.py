from __future__ import annotations

from playtrace.ingest.amcache import AmCacheCollector
from playtrace.ingest.bam import BamCollector
from playtrace.ingest.prefetch import PrefetchCollector
from playtrace.ingest.security_log import SecurityLogCollector
from playtrace.ingest.srum import SrumCollector
from playtrace.ingest.userassist import UserAssistCollector
from playtrace.parsers.bam import BamParser
from playtrace.parsers.base import EvidenceParser, RawCollector
from playtrace.parsers.amcache import AmCacheParser
from playtrace.parsers.prefetch import PrefetchParser
from playtrace.parsers.security_log import SecurityLogParser
from playtrace.parsers.srum import SrumParser
from playtrace.parsers.userassist import UserAssistParser


def build_collectors() -> list[RawCollector]:
    return [
        SecurityLogCollector(),
        PrefetchCollector(),
        UserAssistCollector(),
        AmCacheCollector(),
        SrumCollector(),
        BamCollector(),
    ]


def build_parsers() -> list[EvidenceParser]:
    return [
        SecurityLogParser(),
        PrefetchParser(),
        UserAssistParser(),
        AmCacheParser(),
        SrumParser(),
        BamParser(),
    ]
