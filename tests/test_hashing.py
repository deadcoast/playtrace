from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from playtrace.utils.hashing import Hasher


def test_hasher_hash_string_returns_lowercase_sha1_for_utf8_text() -> None:
    assert Hasher.hash_string("PlayTrace") == "ebe1a32dc6daacfaf595b6abd42f21bdac8bd85b"


@given(st.text(alphabet=st.characters(blacklist_categories=("Cs",))))
def test_hasher_hash_string_matches_hashlib(value: str) -> None:
    assert Hasher.hash_string(value) == hashlib.sha1(value.encode("utf-8")).hexdigest()


@given(st.binary(max_size=4096))
def test_hasher_hash_file_returns_lowercase_sha1_for_file_contents(
    content: bytes,
) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "sample.bin"
        target.write_bytes(content)

        assert Hasher.hash_file(target) == hashlib.sha1(content).hexdigest()


def test_hasher_hash_file_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert Hasher.hash_file(tmp_path / "missing.bin") is None


def test_hasher_hash_file_returns_none_for_permission_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "blocked.bin"
    target.write_bytes(b"blocked")
    original_open = Path.open

    def blocked_open(self: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        if self == target:
            raise PermissionError("blocked")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", blocked_open)

    assert Hasher.hash_file(target) is None


@given(st.binary(max_size=4096))
def test_hasher_hash_file_is_idempotent(content: bytes) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        target = Path(temp_dir) / "repeat.bin"
        target.write_bytes(content)

        assert Hasher.hash_file(target) == Hasher.hash_file(target)
