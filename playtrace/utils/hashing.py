from __future__ import annotations

import hashlib
from collections.abc import Iterator
from pathlib import Path


class Hasher:
    CHUNK_SIZE = 65_536

    @staticmethod
    def hash_file(path: Path | str) -> str | None:
        target = Path(path)
        try:
            with target.open("rb") as handle:
                digest = hashlib.sha1()
                for chunk in Hasher._read_chunks(handle):
                    digest.update(chunk)
                return digest.hexdigest()
        except OSError:
            return None

    @staticmethod
    def hash_string(text: str) -> str:
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _read_chunks(file_handle) -> Iterator[bytes]:
        while True:
            chunk = file_handle.read(Hasher.CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
