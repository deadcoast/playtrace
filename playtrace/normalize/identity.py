from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PureWindowsPath

from playtrace.models.evidence import EvidenceRecord
from playtrace.models.executable import ExecutableIdentity
from playtrace.normalize.pathing import PathNormalizer


@dataclass(slots=True)
class NormalizedEvidence:
    record: EvidenceRecord
    normalized_key: str


class IdentityNormalizer:
    def __init__(self, path_normalizer: PathNormalizer | None = None) -> None:
        self._path_normalizer = path_normalizer or PathNormalizer()

    def build_key(self, record: EvidenceRecord) -> str:
        sha1 = self._string_value(record, "sha1")
        if sha1:
            return f"sha1:{sha1.lower()}"

        canonical_path = self.canonical_path(record)
        if canonical_path:
            return f"path:{canonical_path}"

        basis = "|".join(
            part or ""
            for part in [
                self._string_value(record, "original_filename"),
                self._string_value(record, "product_name"),
                self._string_value(record, "signer"),
            ]
        )
        digest = hashlib.sha1(basis.encode("utf-8", errors="ignore")).hexdigest()
        return f"soft:{digest}"

    def canonical_path(self, record: EvidenceRecord) -> str | None:
        candidate = self._string_value(record, "exe_path")
        if not candidate:
            candidate = self._extract_path_from_command_line(
                self._string_value(record, "command_line")
            )
        return self.normalize_path(candidate)

    def normalize_executable_target(self, target: str | None) -> str | None:
        if target is None:
            return None

        text = target.strip()
        if not text:
            return None

        lowered = text.lower()
        if lowered.startswith("sha1:"):
            suffix = text[5:].strip()
            return f"sha1:{suffix.lower()}" if suffix else None
        if lowered.startswith("soft:"):
            suffix = text[5:].strip()
            return f"soft:{suffix.lower()}" if suffix else None
        if lowered.startswith("path:"):
            canonical_path = self.normalize_path(text[5:])
            return f"path:{canonical_path}" if canonical_path else None

        if self._looks_like_path_target(text):
            canonical_path = self.normalize_path(text)
            return f"path:{canonical_path}" if canonical_path else None

        return None

    def normalize_path(self, path: str | None) -> str | None:
        return self._normalize_path(path)

    def to_executable(self, record: EvidenceRecord) -> ExecutableIdentity:
        key = self.build_key(record)
        canonical_path = self.canonical_path(record)
        filename = None
        if canonical_path:
            filename = PureWindowsPath(canonical_path).name
        else:
            filename = self._string_value(record, "exe_name")

        return ExecutableIdentity(
            exe_id=key,
            normalized_key=key,
            path=self._string_value(record, "exe_path") or canonical_path,
            filename=filename,
            original_filename=self._string_value(record, "original_filename"),
            product_name=self._string_value(record, "product_name"),
            file_description=self._string_value(record, "file_description"),
            signer=self._string_value(record, "signer"),
            company_name=self._string_value(record, "company_name"),
            sha1=self._string_value(record, "sha1"),
            canonical_path=canonical_path,
        )

    def _string_value(self, record: EvidenceRecord, key: str) -> str | None:
        value = record.value.get(key)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _extract_path_from_command_line(self, command_line: str | None) -> str | None:
        if not command_line:
            return None

        text = command_line.strip()
        if not text:
            return None

        if text[0] in {"'", '"'}:
            quote = text[0]
            end = text.find(quote, 1)
            if end > 1:
                return text[1:end]

        lowered = text.lower()
        exe_index = lowered.find(".exe")
        if exe_index >= 0:
            return text[: exe_index + 4]

        return text.split(" ", 1)[0]

    def _normalize_path(self, path: str | None) -> str | None:
        normalized = self._path_normalizer.normalize(path)
        if normalized:
            return normalized

        if not path:
            return None

        stripped = path.strip().strip('"').strip("'")
        if not stripped:
            return None

        normalized = str(PureWindowsPath(stripped.replace("/", "\\")))
        return normalized.lower()

    def _looks_like_windows_path(self, value: str) -> bool:
        stripped = value.strip().strip('"').strip("'")
        if len(stripped) >= 3 and stripped[1] == ":" and stripped[0].isalpha():
            return stripped[2] in {"\\", "/"}
        return stripped.startswith("\\\\") or stripped.startswith("//")

    def _looks_like_path_target(self, value: str) -> bool:
        stripped = value.strip()
        return (
            self._looks_like_windows_path(stripped)
            or ("\\" in stripped)
            or stripped.count("%") >= 2
            or stripped.startswith((".\\", "./"))
            or stripped.lower().endswith(".exe")
        )
