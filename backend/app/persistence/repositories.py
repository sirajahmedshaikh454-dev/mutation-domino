from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.domain.errors import NotFound
from app.domain.models import ProteinInfo, StructureInfo
from app.persistence.database import session_scope
from app.persistence.tables import AnalysisRow, ProteinRow, StructureRow


@dataclass(frozen=True)
class AnalysisRecord:
    id: str
    accession: str
    variant: str
    protein_name: str
    organism: str
    parameters: dict[str, Any]
    result: dict[str, Any]
    warnings: list[str]
    algorithm_version: str
    schema_version: str
    status: str
    created_at: str
    structure_source: str = ""
    model_version: str = ""

    def summary(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "accession": self.accession,
            "variant": self.variant,
            "protein_name": self.protein_name,
            "organism": self.organism,
            "status": self.status,
            "created_at": self.created_at,
            "structure_source": self.structure_source,
            "model_version": self.model_version,
        }

    def envelope(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at,
            "result": self.result,
        }


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class AnalysisRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._factory = session_factory

    def _to_record(self, row: AnalysisRow, structure: StructureRow | None = None) -> AnalysisRecord:
        return AnalysisRecord(
            id=row.id,
            accession=row.accession,
            variant=row.variant,
            protein_name=row.protein_name,
            organism=row.organism,
            parameters=row.parameters_json or {},
            result=row.result_json or {},
            warnings=row.warnings_json or [],
            algorithm_version=row.algorithm_version,
            schema_version=row.schema_version,
            status=row.status,
            created_at=_iso(row.created_at),
            structure_source=structure.source if structure else "",
            model_version=structure.model_version if structure else "",
        )

    def create(
        self,
        *,
        protein: ProteinInfo,
        structure_info: StructureInfo,
        structure_path: str,
        mapping: dict[str, Any],
        variant: str,
        parameters: dict[str, Any],
        result: dict[str, Any],
        algorithm_version: str,
        schema_version: str,
        warnings: list[str],
    ) -> AnalysisRecord:
        with session_scope(self._factory) as session:
            protein_row = session.get(ProteinRow, protein.accession)
            if protein_row is None:
                protein_row = ProteinRow(
                    accession=protein.accession,
                    canonical_sequence=protein.sequence,
                    metadata_json={
                        "name": protein.name,
                        "organism": protein.organism,
                        "gene": protein.gene,
                        "length": protein.length,
                        "source_url": protein.source_url,
                        "retrieved_at": protein.retrieved_at,
                        "source_version": protein.source_version,
                        "mode": protein.mode,
                    },
                    retrieved_at=protein.retrieved_at,
                    source_version=protein.source_version,
                )
                session.add(protein_row)
            else:
                protein_row.canonical_sequence = protein.sequence
                protein_row.metadata_json = {
                    "name": protein.name,
                    "organism": protein.organism,
                    "gene": protein.gene,
                    "length": protein.length,
                    "source_url": protein.source_url,
                    "retrieved_at": protein.retrieved_at,
                    "source_version": protein.source_version,
                    "mode": protein.mode,
                }
                protein_row.retrieved_at = protein.retrieved_at
                protein_row.source_version = protein.source_version

            structure_row = session.scalars(
                select(StructureRow).where(
                    StructureRow.accession == protein.accession,
                    StructureRow.source == structure_info.source,
                    StructureRow.model_version == structure_info.model_version,
                    StructureRow.chain == structure_info.chain,
                )
            ).first()
            if structure_row is None:
                structure_row = StructureRow(
                    accession=protein.accession,
                    source=structure_info.source,
                    model_version=structure_info.model_version,
                    chain=structure_info.chain,
                    file_path=structure_path,
                    checksum=structure_info.checksum_sha256,
                    mapping_json=mapping,
                    retrieved_at=structure_info.retrieved_at,
                )
                session.add(structure_row)
            else:
                structure_row.file_path = structure_path
                structure_row.checksum = structure_info.checksum_sha256
                structure_row.mapping_json = mapping
                structure_row.retrieved_at = structure_info.retrieved_at
            session.flush()

            analysis_id = str(uuid.uuid4())
            row = AnalysisRow(
                id=analysis_id,
                accession=protein.accession,
                structure_id=structure_row.id,
                variant=variant,
                protein_name=protein.name,
                organism=protein.organism,
                parameters_json=parameters,
                result_json=result,
                algorithm_version=algorithm_version,
                schema_version=schema_version,
                status="completed",
                warnings_json=warnings,
            )
            session.add(row)
            session.flush()
            record = self._to_record(row, structure_row)
        return record

    def get(self, analysis_id: str) -> AnalysisRecord:
        with session_scope(self._factory) as session:
            row = session.get(AnalysisRow, analysis_id)
            if row is None:
                raise NotFound("Analysis not found.", details={"analysis_id": analysis_id})
            structure = session.get(StructureRow, row.structure_id) if row.structure_id else None
            return self._to_record(row, structure)

    def list(self, *, limit: int = 20, offset: int = 0) -> tuple[list[AnalysisRecord], int]:
        with session_scope(self._factory) as session:
            total = session.scalar(select(func.count()).select_from(AnalysisRow)) or 0
            rows = session.scalars(
                select(AnalysisRow)
                .order_by(AnalysisRow.created_at.desc(), AnalysisRow.id.desc())
                .limit(limit)
                .offset(offset)
            ).all()
            records: list[AnalysisRecord] = []
            for row in rows:
                structure = session.get(StructureRow, row.structure_id) if row.structure_id else None
                records.append(self._to_record(row, structure))
            return records, int(total)
