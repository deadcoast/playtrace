from __future__ import annotations

import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from playtrace.normalize.metadata import ExecutableMetadata, MetadataExtractor

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pe"
EMPTY_METADATA = ExecutableMetadata(
    product_name=None,
    original_filename=None,
    file_description=None,
    company_name=None,
    signer=None,
)


@given(st.text(alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")), min_size=1, max_size=24))
def test_metadata_extractor_returns_empty_metadata_for_invalid_inputs(name: str) -> None:
    extractor = MetadataExtractor()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        missing = temp_path / f"{name}.exe"
        non_pe = temp_path / f"{name}.txt"
        non_pe.write_text("not a pe file", encoding="utf-8")

        assert extractor.extract(missing) == EMPTY_METADATA
        assert extractor.extract(non_pe) == EMPTY_METADATA


@given(st.one_of(st.none(), st.text()))
def test_metadata_extractor_normalizes_strings(value: str | None) -> None:
    extractor = MetadataExtractor()
    expected = None if value is None else value.strip() or None
    candidate = None if value is None else f"  {value}  "

    assert extractor._normalize_field(candidate) == expected


@given(
    st.sampled_from(
        [
            FIXTURES / "signed_with_version.exe",
            FIXTURES / "unsigned_with_version.exe",
            FIXTURES / "signed_no_version.dll",
        ]
    )
)
def test_metadata_extractor_is_idempotent_for_valid_pe_fixtures(path: Path) -> None:
    extractor = MetadataExtractor()

    assert extractor.extract(path) == extractor.extract(path)


def test_metadata_extractor_reads_signed_pe_with_version_info() -> None:
    metadata = MetadataExtractor().extract(FIXTURES / "signed_with_version.exe")

    assert metadata == ExecutableMetadata(
        product_name="Python",
        original_filename="python.exe",
        file_description="Python",
        company_name="Python Software Foundation",
        signer="Python Software Foundation",
    )


def test_metadata_extractor_reads_unsigned_pe_with_version_info() -> None:
    metadata = MetadataExtractor().extract(FIXTURES / "unsigned_with_version.exe")

    assert metadata == ExecutableMetadata(
        product_name="Simple Launcher",
        original_filename="t64.exe",
        file_description="Simple Launcher Executable",
        company_name="Simple Launcher User",
        signer=None,
    )


def test_metadata_extractor_reads_signed_pe_without_version_info() -> None:
    metadata = MetadataExtractor().extract(FIXTURES / "signed_no_version.dll")

    assert metadata == ExecutableMetadata(
        product_name=None,
        original_filename=None,
        file_description=None,
        company_name=None,
        signer="Python Software Foundation",
    )


def test_metadata_extractor_returns_empty_metadata_for_missing_file() -> None:
    metadata = MetadataExtractor().extract(FIXTURES / "missing.exe")

    assert metadata == EMPTY_METADATA
