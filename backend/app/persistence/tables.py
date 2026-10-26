from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class ProteinRow(Base):
    __tablename__ = "proteins"

    accession: Mapped[str] = mapped_column(String(20), primary_key=True)
    canonical_sequence: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieved_at: Mapped[str] = mapped_column(String(40), nullable=False)
    source_version: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    structures: Mapped[list[StructureRow]] = relationship(back_populates="protein")


class StructureRow(Base):
    __tablename__ = "structures"
    __table_args__ = (UniqueConstraint("accession", "source", "model_version", "chain", name="uq_structure"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    accession: Mapped[str] = mapped_column(ForeignKey("proteins.accession"), index=True, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    chain: Mapped[str] = mapped_column(String(8), nullable=False, default="")
    file_path: Mapped[str] = mapped_column(Text, nullable=False, default="")
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    mapping_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    retrieved_at: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    protein: Mapped[ProteinRow] = relationship(back_populates="structures")


class AnalysisRow(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    accession: Mapped[str] = mapped_column(ForeignKey("proteins.accession"), index=True, nullable=False)
    structure_id: Mapped[int | None] = mapped_column(ForeignKey("structures.id"), nullable=True)
    variant: Mapped[str] = mapped_column(String(16), nullable=False)
    protein_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    organism: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    parameters_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    algorithm_version: Mapped[str] = mapped_column(String(20), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
    warnings_json: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
