from __future__ import annotations

import sys
from pathlib import Path

import pytest

from playtrace.normalize.metadata import MetadataExtractor


def test_extract_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert MetadataExtractor().extract(tmp_path / "missing.exe") is None


def test_extract_returns_none_for_non_pe_file(tmp_path: Path) -> None:
    target = tmp_path / "sample.txt"
    target.write_text("not a portable executable", encoding="utf-8")

    assert MetadataExtractor().extract(target) is None


@pytest.mark.skipif(
    Path(sys.executable).suffix.lower() != ".exe",
    reason="Requires a Windows PE executable",
)
def test_extract_is_idempotent_for_a_valid_pe_file() -> None:
    extractor = MetadataExtractor()

    first = extractor.extract(sys.executable)
    second = extractor.extract(sys.executable)

    assert first is not None
    assert first == second


def test_normalize_field_strips_whitespace() -> None:
    extractor = MetadataExtractor()

    assert extractor._normalize_field("  Playtrace  ") == "Playtrace"
    assert extractor._normalize_field("   ") is None
    assert extractor._normalize_field(None) is None


@pytest.mark.skipif(
    not Path(r"C:\Windows\System32\cmd.exe").exists(),
    reason="Requires a signed Windows system executable",
)
def test_extract_reads_signer_for_signed_windows_binary() -> None:
    metadata = MetadataExtractor().extract(r"C:\Windows\System32\cmd.exe")

    assert metadata is not None
    assert metadata.signer is not None
    assert "Microsoft" in metadata.signer
