from __future__ import annotations

import hashlib
from dataclasses import dataclass

from playtrace.models.artifacts import ArtifactRecord
from playtrace.models.executable import ExecutableIdentity


@dataclass(slots=True)
class NormalizedArtifact:
    artifact: ArtifactRecord
    normalized_key: str


class IdentityNormalizer:
    def build_key(self, artifact: ArtifactRecord) -> str:
        if artifact.sha1:
            return f"sha1:{artifact.sha1.lower()}"

        basis = "|".join(
            part or ""
            for part in [
                artifact.exe_path,
                artifact.original_filename,
                artifact.product_name,
                artifact.signer,
            ]
        )
        digest = hashlib.sha1(basis.encode("utf-8", errors="ignore")).hexdigest()
        return f"soft:{digest}"

    def to_executable(self, artifact: ArtifactRecord) -> ExecutableIdentity:
        key = self.build_key(artifact)
        return ExecutableIdentity(
            exe_id=key,
            normalized_key=key,
            path=artifact.exe_path,
            filename=artifact.exe_name,
            original_filename=artifact.original_filename,
            product_name=artifact.product_name,
            file_description=artifact.file_description,
            signer=artifact.signer,
            company_name=artifact.company_name,
            sha1=artifact.sha1,
        )