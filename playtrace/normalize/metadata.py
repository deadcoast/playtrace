from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ExecutableMetadata:
    product_name: str | None = None
    original_filename: str | None = None
    file_description: str | None = None
    company_name: str | None = None
    signer: str | None = None


class MetadataExtractor:
    _FIELDS = (
        "ProductName",
        "OriginalFilename",
        "FileDescription",
        "CompanyName",
    )

    def extract(self, path: str | Path) -> ExecutableMetadata | None:
        target = Path(path)
        if not target.is_file() or not self._is_pe_file(target):
            return None

        fields = self._extract_version_info(target)
        return ExecutableMetadata(
            product_name=self._normalize_field(fields.get("ProductName")),
            original_filename=self._normalize_field(fields.get("OriginalFilename"))
            or self._normalize_field(target.name),
            file_description=self._normalize_field(fields.get("FileDescription")),
            company_name=self._normalize_field(fields.get("CompanyName")),
            signer=self._normalize_field(self._extract_signature(target)),
        )

    def _extract_version_info(self, path: Path) -> dict[str, str | None]:
        if os.name != "nt":
            return {}

        try:
            import ctypes
            from ctypes import wintypes
        except ImportError:
            return {}

        class _LangCodePage(ctypes.Structure):
            _fields_ = [
                ("language", wintypes.WORD),
                ("code_page", wintypes.WORD),
            ]

        version = ctypes.windll.version
        size = version.GetFileVersionInfoSizeW(str(path), None)
        if not size:
            return {}

        buffer = ctypes.create_string_buffer(size)
        if not version.GetFileVersionInfoW(str(path), 0, size, buffer):
            return {}

        candidates = self._translation_candidates(
            buffer,
            version,
            ctypes,
            wintypes,
            _LangCodePage,
        )

        values: dict[str, str | None] = {}
        for field in self._FIELDS:
            values[field] = None
            for language, code_page in candidates:
                query = f"\\StringFileInfo\\{language:04x}{code_page:04x}\\{field}"
                text = self._query_string_value(
                    buffer,
                    query,
                    version,
                    ctypes,
                    wintypes,
                )
                if text:
                    values[field] = text
                    break
        return values

    def _extract_signature(self, path: Path) -> str | None:
        if os.name != "nt":
            return None
        if self._is_current_process_binary(path):
            return None

        command = [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            (
                "$signature = Get-AuthenticodeSignature -LiteralPath $args[0]; "
                "if ($signature.Status -eq 'Valid' -and $signature.SignerCertificate) { "
                "$signature.SignerCertificate.Subject "
                "}"
            ),
            str(path),
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="ignore",
                timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None

        if completed.returncode != 0:
            return None

        subject = completed.stdout.strip()
        if not subject:
            return None
        match = re.search(r"(?:^|,\s*)CN=([^,]+)", subject)
        return match.group(1).strip() if match else subject

    def _normalize_field(self, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None

    def _is_pe_file(self, path: Path) -> bool:
        try:
            with path.open("rb") as handle:
                return handle.read(2) == b"MZ"
        except OSError:
            return False

    def _is_current_process_binary(self, path: Path) -> bool:
        try:
            return path.resolve() == Path(sys.executable).resolve()
        except OSError:
            return False

    def _translation_candidates(
        self,
        buffer,
        version,
        ctypes,
        wintypes,
        translation_type,
    ) -> list[tuple[int, int]]:
        pointer = ctypes.c_void_p()
        length = wintypes.UINT()
        if version.VerQueryValueW(
            buffer,
            "\\VarFileInfo\\Translation",
            ctypes.byref(pointer),
            ctypes.byref(length),
        ):
            count = length.value // ctypes.sizeof(translation_type)
            translations = ctypes.cast(
                pointer,
                ctypes.POINTER(translation_type * count),
            ).contents
            candidates = [
                (entry.language, entry.code_page)
                for entry in translations
            ]
            if candidates:
                return candidates
        return [(0x0409, 0x04B0), (0x0409, 0x04E4)]

    def _query_string_value(
        self,
        buffer,
        query: str,
        version,
        ctypes,
        wintypes,
    ) -> str | None:
        pointer = ctypes.c_void_p()
        length = wintypes.UINT()
        if not version.VerQueryValueW(
            buffer,
            query,
            ctypes.byref(pointer),
            ctypes.byref(length),
        ):
            return None
        if not pointer.value:
            return None
        return ctypes.wstring_at(pointer.value, max(length.value - 1, 0))
