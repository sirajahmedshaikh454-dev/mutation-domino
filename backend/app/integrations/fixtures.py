from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.core.time import utc_now_iso
from app.domain.errors import ProteinNotFound, StructureUnavailable
from app.domain.models import ProteinInfo, StructureInfo
from app.integrations.alphafold import AlphaFoldArtifact
from app.integrations.uniprot import protein_info_from_payload

FIXTURE_ACCESSIONS = ("P69905", "P04637")


class FixtureProvider:
    """Serves recorded P69905 responses for offline development, tests, and E2E."""

    def __init__(self, fixture_dir: Path) -> None:
        self.fixture_dir = fixture_dir

    def supports(self, accession: str) -> bool:
        return accession in FIXTURE_ACCESSIONS

    def _ensure(self, accession: str) -> None:
        if not self.supports(accession):
            raise ProteinNotFound(
                "Fixture mode contains recorded data only for P69905 and P04637. "
                "Set MUTATION_DOMINO_MODE=live to query UniProt.",
                details={"accession": accession, "available": list(FIXTURE_ACCESSIONS), "mode": "fixture"},
            )

    def protein(self, accession: str) -> ProteinInfo:
        self._ensure(accession)
        path = self.fixture_dir / f"uniprot_{accession}.json"
        if not path.is_file():
            raise ProteinNotFound("Recorded UniProt fixture is missing.", details={"accession": accession})
        payload = json.loads(path.read_text(encoding="utf-8"))
        return protein_info_from_payload(
            payload,
            source_url=f"fixture://uniprot/uniprot_{accession}.json",
            retrieved_at="2026-10-25T00:00:00Z",
            mode="fixture",
        )

    def alphafold_metadata(self, accession: str) -> dict[str, Any]:
        self._ensure(accession)
        path = self.fixture_dir / f"alphafold_{accession}.json"
        if not path.is_file():
            raise StructureUnavailable("Recorded AlphaFold fixture is missing.")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list) or not payload:
            raise StructureUnavailable("Recorded AlphaFold fixture is empty.")
        return payload[0]

    def structure(self, accession: str) -> AlphaFoldArtifact:
        self._ensure(accession)
        path = self.fixture_dir / f"af_{accession}.cif"
        if not path.is_file():
            raise StructureUnavailable("Recorded AlphaFold structure fixture is missing.")
        payload = path.read_bytes()
        entry = self.alphafold_metadata(accession)
        checksum = hashlib.sha256(payload).hexdigest()
        return AlphaFoldArtifact(
            payload=payload,
            suffix=".cif",
            metadata=entry,
            structure_info=StructureInfo(
                accession=accession,
                source="AlphaFold DB (recorded fixture)",
                model_version=f"v{entry.get('latestVersion', 6)}",
                chain=str(entry.get("chainId") or "A"),
                url=f"fixture://alphafold/af_{accession}.cif",
                checksum_sha256=checksum,
                retrieved_at=utc_now_iso(),
                is_predicted=True,
                confidence_source="plddt",
                file_format="cif",
                file_size_bytes=len(payload),
                tool_used=str(entry.get("toolUsed") or "AlphaFold"),
                model_created_date=str(entry.get("modelCreatedDate") or ""),
                mode="fixture",
            ),
        )
