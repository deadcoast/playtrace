from __future__ import annotations

import hashlib
from pathlib import Path


class Hasher:
    _CHUNK_SIZE = 64 * 1024

    @staticmethod
    def hash_string(value: str) -> str:
        return hashlib.sha1(value.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_file(path: str | Path) -> str | None:
        digest = hashlib.sha1()
        candidate = Path(path)

        try:
            with candidate.open("rb") as handle:
                while chunk := handle.read(Hasher._CHUNK_SIZE):
                    digest.update(chunk)
        except (FileNotFoundError, PermissionError, OSError):
            return None

        return digest.hexdigest()
