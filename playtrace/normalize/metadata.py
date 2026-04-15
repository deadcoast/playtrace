from __future__ import annotations

import ctypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ctypes import wintypes

from playtrace.utils.platform import PlatformDetector

try:
    import pefile  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - dependency is expected in the project environment
    pefile = None  # type: ignore[assignment]

try:
    import win32crypt  # type: ignore[import-untyped]
    import win32cryptcon  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - dependency is expected on Windows only
    win32crypt = None  # type: ignore[assignment]
    win32cryptcon = None  # type: ignore[assignment]

if TYPE_CHECKING:
    import pefile as pefile_types


@dataclass(slots=True)
class ExecutableMetadata:
    product_name: str | None
    original_filename: str | None
    file_description: str | None
    company_name: str | None
    signer: str | None


class _CertNameBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


class MetadataExtractor:
    _EMPTY = ExecutableMetadata(
        product_name=None,
        original_filename=None,
        file_description=None,
        company_name=None,
        signer=None,
    )

    def extract(self, path: str | Path) -> ExecutableMetadata:
        candidate = Path(path)
        if pefile is None:
            return self._EMPTY

        try:
            pe = pefile.PE(str(candidate))
        except Exception:
            return self._EMPTY

        try:
            pe.parse_data_directories(
                directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
            )
            version_info = self._extract_version_info(pe)
        except Exception:
            version_info = {}
        finally:
            pe.close()

        return ExecutableMetadata(
            product_name=self._normalize_field(version_info.get("ProductName")),
            original_filename=self._normalize_field(version_info.get("OriginalFilename")),
            file_description=self._normalize_field(version_info.get("FileDescription")),
            company_name=self._normalize_field(version_info.get("CompanyName")),
            signer=self._normalize_field(self._extract_signature(candidate)),
        )

    def _extract_version_info(self, pe: pefile_types.PE) -> dict[str, str]:
        version_info: dict[str, str] = {}

        for entry_group in getattr(pe, "FileInfo", []) or []:
            for entry in entry_group:
                if getattr(entry, "Key", b"") != b"StringFileInfo" or not hasattr(entry, "StringTable"):
                    continue

                for table in entry.StringTable:
                    for key, value in table.entries.items():
                        version_info[self._decode_text(key)] = self._decode_text(value)

        return version_info

    def _extract_signature(self, path: Path) -> str | None:
        if PlatformDetector.detect().windows_version is None:
            return None
        if win32crypt is None or win32cryptcon is None:
            return None

        store = None
        message = None

        try:
            query = win32crypt.CryptQueryObject(
                win32cryptcon.CERT_QUERY_OBJECT_FILE,
                str(path),
                win32cryptcon.CERT_QUERY_CONTENT_FLAG_ALL,
                win32cryptcon.CERT_QUERY_FORMAT_FLAG_ALL,
                0,
            )
            store = query.get("CertStore")
            message = query.get("Msg")
            if store is None:
                return None

            certificates = list(store.CertEnumCertificatesInStore())
            signer_certificate = self._select_signer_certificate(certificates)
            if signer_certificate is None:
                return None

            subject = self._name_blob_to_string(
                signer_certificate.CertEncodingType,
                signer_certificate.Subject,
                win32cryptcon.CERT_X500_NAME_STR,
            )
            if not subject:
                return None

            match = re.search(r"(?:^|,\s*)CN=([^,]+)", subject)
            return match.group(1).strip() if match else subject.strip() or None
        except Exception:
            return None
        finally:
            if message is not None:
                try:
                    message.CryptMsgClose()
                except Exception:
                    pass
            if store is not None:
                try:
                    store.CertCloseStore()
                except Exception:
                    pass

    def _normalize_field(self, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    def _select_signer_certificate(self, certificates: list[Any]) -> Any | None:
        if not certificates:
            return None

        certificate_data: list[tuple[object, str | None, str | None]] = []
        for certificate in certificates:
            subject = self._name_blob_to_string(
                certificate.CertEncodingType,
                certificate.Subject,
                win32cryptcon.CERT_X500_NAME_STR,
            )
            issuer = self._name_blob_to_string(
                certificate.CertEncodingType,
                certificate.Issuer,
                win32cryptcon.CERT_X500_NAME_STR,
            )
            certificate_data.append((certificate, subject, issuer))

        issuer_names = {issuer for _, _, issuer in certificate_data if issuer}
        for certificate, subject, issuer in certificate_data:
            if subject and subject != issuer and subject not in issuer_names:
                return certificate

        for certificate, subject, issuer in certificate_data:
            if subject and subject != issuer:
                return certificate

        return certificate_data[0][0]

    def _name_blob_to_string(
        self,
        encoding_type: int,
        blob_bytes: bytes,
        style: int,
    ) -> str | None:
        win_dll = getattr(ctypes, "WinDLL", None)
        if win_dll is None or not blob_bytes:
            return None

        crypt32 = win_dll("crypt32", use_last_error=True)
        crypt32.CertNameToStrW.argtypes = [
            wintypes.DWORD,
            ctypes.POINTER(_CertNameBlob),
            wintypes.DWORD,
            wintypes.LPWSTR,
            wintypes.DWORD,
        ]
        crypt32.CertNameToStrW.restype = wintypes.DWORD

        buffer = (ctypes.c_ubyte * len(blob_bytes)).from_buffer_copy(blob_bytes)
        blob = _CertNameBlob(len(blob_bytes), buffer)

        required = crypt32.CertNameToStrW(encoding_type, ctypes.byref(blob), style, None, 0)
        if required == 0:
            return None

        output = ctypes.create_unicode_buffer(required)
        written = crypt32.CertNameToStrW(encoding_type, ctypes.byref(blob), style, output, required)
        if written == 0:
            return None

        text = output.value.strip()
        return text or None

    def _decode_text(self, value: bytes | str) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
        return value
