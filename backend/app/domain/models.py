from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass(frozen=True)
class ProteinInfo:
    accession: str
    name: str
    organism: str
    sequence: str
    length: int
    gene: str | None = None
    source_url: str = ""
    retrieved_at: str = ""
    source_version: str = ""
    mode: str = "live"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "name": self.name,
            "organism": self.organism,
            "gene": self.gene,
            "length": self.length,
            "sequence": self.sequence,
            "provenance": {
                "source": "UniProt REST",
                "source_url": self.source_url,
                "retrieved_at": self.retrieved_at,
                "source_version": self.source_version,
                "mode": self.mode,
            },
        }


@dataclass(frozen=True)
class StructureInfo:
    accession: str
    source: str
    model_version: str
    chain: str
    url: str
    checksum_sha256: str
    retrieved_at: str
    is_predicted: bool
    confidence_source: Literal["plddt", "b_factor", "none"]
    file_format: str
    file_size_bytes: int
    tool_used: str = ""
    model_created_date: str = ""
    mode: str = "live"

    def to_dict(self) -> dict[str, Any]:
        return {
            "accession": self.accession,
            "source": self.source,
            "is_predicted": self.is_predicted,
            "confidence_source": self.confidence_source,
            "model_version": self.model_version,
            "chain": self.chain,
            "url": self.url,
            "checksum_sha256": self.checksum_sha256,
            "retrieved_at": self.retrieved_at,
            "file_format": self.file_format,
            "file_size_bytes": self.file_size_bytes,
            "tool_used": self.tool_used,
            "model_created_date": self.model_created_date,
            "mode": self.mode,
        }


@dataclass(frozen=True)
class AnalysisParameters:
    ca_radius_angstrom: float = 8.0
    heavy_atom_radius_angstrom: float = 5.0

    def to_dict(self) -> dict[str, float]:
        return {
            "ca_radius_angstrom": self.ca_radius_angstrom,
            "heavy_atom_radius_angstrom": self.heavy_atom_radius_angstrom,
        }
