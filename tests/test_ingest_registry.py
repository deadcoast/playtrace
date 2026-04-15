from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

import pytest

from playtrace.ingest.prefetch import PrefetchCollector
from playtrace.ingest.registry import build_parsers
from playtrace.ingest.security_log import SecurityLogCollector
from playtrace.ingest.srum import SrumCollector
from playtrace.ingest.userassist import UserAssistCollector
from playtrace.models.evidence import RawArtifact
from playtrace.parsers.amcache import AmCacheParser
from playtrace.parsers.bam import BamParser
from playtrace.parsers.base import CollectContext
from playtrace.parsers.prefetch import PrefetchParser
from playtrace.parsers.security_log import SecurityLogParser
from playtrace.parsers.srum import SrumParser
from playtrace.parsers.userassist import UserAssistParser


@pytest.mark.parametrize(
    "parser_type",
    [
        SecurityLogParser,
        PrefetchParser,
        UserAssistParser,
        AmCacheParser,
        SrumParser,
        BamParser,
    ],
)
def test_parsers_declare_sequence_artifact_contract(parser_type: type[object]) -> None:
    annotation = get_type_hints(parser_type.parse)["artifacts"]

    assert get_origin(annotation).__name__ == "Sequence"
    assert get_args(annotation) == (RawArtifact,)


def test_build_parsers_returns_protocol_compatible_instances() -> None:
    context = CollectContext(
        scan_run_id="scan:test",
        host_name="demo-host",
        temp_dir=Path("."),
        full_scan=False,
    )
    sample_artifacts = [
        SecurityLogCollector().collect(context)[0],
        PrefetchCollector().collect(context)[0],
        UserAssistCollector().collect(context)[0],
        SrumCollector().collect(context)[0],
    ]
    artifacts_by_source = {artifact.source.value: artifact for artifact in sample_artifacts}

    for parser in build_parsers():
        artifact = artifacts_by_source.get(parser.name)
        if artifact is None:
            continue

        records = parser.parse((artifact,))
        assert records


def test_sample_collectors_emit_timezone_aware_observed_at_values(tmp_path) -> None:
    context = CollectContext(
        scan_run_id="scan:test",
        host_name="demo-host",
        temp_dir=tmp_path,
        full_scan=False,
    )

    security_artifact = SecurityLogCollector().collect(context)[0]
    prefetch_artifact = PrefetchCollector().collect(context)[0]
    userassist_artifact = UserAssistCollector().collect(context)[0]
    srum_artifact = SrumCollector().collect(context)[0]

    assert security_artifact.observed_at == datetime(2026, 4, 11, 18, 42, 3, tzinfo=timezone.utc)
    assert prefetch_artifact.observed_at == datetime(2026, 4, 11, 18, 42, 5, tzinfo=timezone.utc)
    assert userassist_artifact.observed_at == datetime(2026, 4, 11, 18, 41, 50, tzinfo=timezone.utc)
    assert srum_artifact.observed_at == datetime(2026, 4, 11, 18, 0, 0, tzinfo=timezone.utc)
