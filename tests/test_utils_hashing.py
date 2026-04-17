from __future__ import annotations

import hashlib
from pathlib import Path

from playtrace.utils.hashing import Hasher


def test_hash_string_returns_lowercase_sha1() -> None:
    assert Hasher.hash_string("playtrace") == hashlib.sha1(b"playtrace").hexdigest()


def test_hash_file_streams_file_contents(tmp_path: Path) -> None:
    target = tmp_path / "sample.bin"
    target.write_bytes(b"playtrace" * 1000)

    assert Hasher.hash_file(target) == hashlib.sha1(target.read_bytes()).hexdigest()


def test_hash_file_returns_none_for_missing_files(tmp_path: Path) -> None:
    assert Hasher.hash_file(tmp_path / "missing.bin") is None
